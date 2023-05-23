# Note: the module name is psycopg, not psycopg3
from lib import arxiv, util, twitter
from typing import List, Dict, Any, Iterable
from enum import Enum
from psycopg_pool import ConnectionPool
import psycopg
import uuid
from datetime import datetime
from typing import NamedTuple, Optional
import json
import pydantic
import yaml

""""
discarding closed connection: <psycopg.Connection [BAD] at 0x7fcc04da7d30>
ERROR:root:consuming input failed: terminating connection due to idle-session timeout
DETAIL:  https://docs.bit.io/docs/trouble-shooting-common-connection-issues#connection-timeouts
HINT:  Add a retry or connection pool
SSL connection has been closed unexpectedly

"""


class PostgresCredentials(pydantic.BaseModel):
    dev_url: str
    prod_url: str


class Tables(str, Enum):
    ARXIV = "Arxiv"
    ARXIV_AUTHORS = "ArxivAuthor"
    ARXIV_CATEGORY = "ArxivCategory"
    TWEET = "Tweet"
    ARXIV_TWEET = "ArxivTweet"


class ArxivEntity(pydantic.BaseModel):
    paper: arxiv.ArxivPaper
    likes: Optional[int] = None
    retweets: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None
    impressions: Optional[int] = None


class SimilarityResult(pydantic.BaseModel):
    entity: ArxivEntity
    similarity: float


PRIMARY_KEYS = {
    Tables.ARXIV: ("arxiv_id",),
    Tables.ARXIV_AUTHORS: ("arxiv_id", "author"),
    Tables.ARXIV_CATEGORY: ("arxiv_id", "category"),
    Tables.TWEET: ("tweet_id",),
    Tables.ARXIV_TWEET: ("arxiv_id", "tweet_id"),
}

GENERATED_COLUMNS = {Tables.ARXIV: ("text_search_vector",)}

MAX_AUTHOR_LEN = 256
MAX_CATEGORY_LEN = 32
SOCIAL_ARXIV_COLUMNS = ["likes", "retweets", "replies", "quotes", "impressions"]


class Database:
    """Contains methods for interacting with the backend PostgreSQL database."""

    def __init__(self):
        with open("private/postgres_auth.yaml", "r") as f:
            credentials = PostgresCredentials.parse_obj(yaml.safe_load(f))
        self._pool = ConnectionPool(credentials.dev_url)
        self._table_columns = {}

    def create_tables(self, embedding_dim=384):
        """Creates the necessary tables, assuming embeddings are `embedding_dim` size."""
        q = []
        # Arxiv Table Query
        q.append(
            f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV} (
            arxiv_id VARCHAR(12),
            title TEXT,
            abstract TEXT,
            published_ts TIMESTAMP,
            embedding vector({embedding_dim}),
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            quotes INTEGER,
            impressions BIGINT

            PRIMARY KEY (arxiv_id)
        );

        ALTER TABLE {Tables.ARXIV}
            ADD COLUMN text_search_vector tsvector
                    GENERATED ALWAYS AS 
                    (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, ''))) STORED;
        """
        )

        # Tweet Table Query
        q.append(
            f"""
        CREATE TABLE IF NOT EXISTS {Tables.TWEET} (
            tweet_id BIGINT,
            created_at TIMESTAMP,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            quotes INTEGER,
            impressions BIGINT,

            PRIMARY KEY (tweet_id)
        );
        """
        )

        # Arxiv Authors Table Query
        q.append(
            f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV_AUTHORS} (
            arxiv_id VARCHAR(12),
            author VARCHAR({MAX_AUTHOR_LEN}),

            PRIMARY KEY (arxiv_id, author),

            CONSTRAINT fk_author_arxiv
                FOREIGN KEY (arxiv_id)
                REFERENCES {Tables.ARXIV}(arxiv_id)
        );
        """
        )

        # Arxiv Category Table Query
        q.append(
            f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV_CATEGORY} (
            arxiv_id VARCHAR(12),
            category VARCHAR({MAX_CATEGORY_LEN}),

            PRIMARY KEY (arxiv_id, category),

            CONSTRAINT fk_arxivcategory_arxiv
                FOREIGN KEY (arxiv_id)
                REFERENCES {Tables.ARXIV}(arxiv_id)
        );
        """
        )

        # Arxiv Tweet Table Query
        q.append(
            f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV_TWEET} (
            arxiv_id VARCHAR(12),
            tweet_id BIGINT,

            PRIMARY KEY (arxiv_id, tweet_id),

            CONSTRAINT fk_arxivtweet_arxiv
                FOREIGN KEY (arxiv_id)
                REFERENCES {Tables.ARXIV}(arxiv_id),

            CONSTRAINT fk_arxivtweet_tweet
                FOREIGN KEY (tweet_id)
                REFERENCES {Tables.TWEET}(tweet_id)
        );
        """
        )

        with self._pool.connection() as conn:
            for t in q:
                conn.execute(t)
            conn.commit()

    def delete_tables(self):
        """Deletes all the tables."""
        with self._pool.connection() as conn:
            for t in Tables:
                conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    def get_table_columns(self, table: Tables):
        """Returns a list of a table's columns. Runs a query on the first call
        but caches the result.
        """
        if table not in self._table_columns:
            generated_cols = GENERATED_COLUMNS.get(table, set())
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT * FROM {table} LIMIT 0")
                    self._table_columns[table] = [
                        desc[0]
                        for desc in cur.description
                        if desc[0] not in generated_cols
                    ]
        return self._table_columns[table][:]

    def _format_record_to_tuple(self, record, cols):
        return tuple([record.get(c) for c in cols])

    def bulk_insert(
        self, table, records: Iterable[Dict[str, Any]], insert_cols=None, overwrite=True
    ):
        """Performs a bulk insert of rows into the database. See _bulk_insert."""
        with self._pool.connection() as conn:
            with conn.cursor() as cursor:
                self._bulk_insert(
                    table,
                    records,
                    insert_cols=insert_cols,
                    overwrite=overwrite,
                    cursor=cursor,
                )

    def _bulk_insert(
        self,
        table,
        records: Iterable[Dict[str, Any]],
        cursor,
        insert_cols=None,
        overwrite=True,
    ):
        """Performs a bulk insert of rows into the database. The rows are uploaded to a
        temp table, and then inserted into the existing table. If a row with the same
        primary key already exists, it will be overwritten if overwrite == True or left alone if
        overwrite == False.

        Only columns in `insert_cols` will be written. If `insert_cols` is None, it will default to
        all columns in the table. Any columns in the table that
        are not populated in the record will have value NULL.

        Args:
            table: Table to insert into.
            records: Records to insert.
            insert_cols: Columns to insert.
            overwrite: Whether to overwrite conflicting rows (upsert vs. insert)
            cursor: Database connection cursor to use.
        """
        id_cols = PRIMARY_KEYS[table]
        temp_table_id = f"{table}_tmp_{str(uuid.uuid4())[:6]}"
        insert_cols = (
            self.get_table_columns(table) if insert_cols is None else insert_cols
        )
        insert_cols = list(set(insert_cols).union(id_cols))
        insert_cols_str = ",".join(insert_cols)
        cur = cursor

        cur.execute(
            f"""
            CREATE TEMPORARY TABLE {temp_table_id} 
            ON COMMIT DROP
            AS SELECT {insert_cols_str} FROM {table} LIMIT 0
            """
        )
        with cur.copy(f"COPY {temp_table_id} FROM STDIN") as copy:
            for record in records:
                record = self._format_record_to_tuple(record, insert_cols)
                copy.write_row(record)

        if overwrite:
            # Update inserted columns, leave others alone
            update_set = ",".join(
                [f"{c}=excluded.{c}" for c in insert_cols if c not in id_cols]
            )
            conflict = f"DO UPDATE SET {update_set}"
        else:
            conflict = "DO NOTHING"
        cur.execute(
            f"""
        INSERT INTO {table}({insert_cols_str})
        SELECT {insert_cols_str} FROM {temp_table_id}
        ON CONFLICT ({','.join(id_cols)}) {conflict}
        """
        )

    def insert_tweets(self, tweets: List[twitter.ArxivTweet]):
        """Inserts tweets into the database. Creates blank entries in Arxiv table if necessary
        and creates entries in the ArxivTweet table.

        Args:
            tweets: Tweets to insert.
        """

        def tweets_to_insert():
            for t in tweets:
                yield {
                    "tweet_id": t.tweet_id,
                    "likes": t.likes,
                    "retweets": t.retweets,
                    "replies": t.replies,
                    "quotes": t.quotes,
                    "impressions": t.impressions,
                    "created_at": t.created_at,
                }

        def papers_to_insert():
            for t in tweets:
                for i in t.arxiv_ids:
                    yield {"arxiv_id": i}

        def references_to_insert():
            for t in tweets:
                for i in t.arxiv_ids:
                    yield {"tweet_id": t.tweet_id, "arxiv_id": i}

        # Clean up any tweets that have been edited and now have a newer version
        tweets_to_delete = set()
        for t in tweets:
            tweets_to_delete.update(t.edited_tweet_ids)

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                # Insert tweets
                self._bulk_insert(
                    table=Tables.TWEET,
                    records=tweets_to_insert(),
                    overwrite=True,
                    cursor=cur,
                )
                # Delete edits (TODO)

                # Delete arxiv posts referenced by edits? (no it's fine)

                # Insert blank papers into arxiv table if any not present.
                # We can handle arxiv papers later.
                self._bulk_insert(
                    table=Tables.ARXIV,
                    records=papers_to_insert(),
                    overwrite=False,
                    cursor=cur,
                )

                # Update reference table
                self._bulk_insert(
                    table=Tables.ARXIV_TWEET,
                    records=references_to_insert(),
                    overwrite=False,
                    cursor=cur,
                )

    def insert_papers(self, papers: List[arxiv.ArxivPaper], insert_type=None):
        """Inserts papers into the database. Also updates author and category tables.

        Args:
            papers: Papers to insert.
            insert_type: Can be None to insert all paper attributes (excluding social), "embedding" to only
                insert embeddings, or "social" to only insert likes, retweets, etc.
        """
        if insert_type is None:
            insert_cols = ["arxiv_id", "abstract", "title", "published_ts", "embedding"]
        elif insert_type == "embeddings":
            insert_cols = ["embedding"]
        else:
            raise ValueError("Invalid insert type")

        def papers_to_insert():
            for p in papers:
                yield {
                    "arxiv_id": p.arxiv_id,
                    "abstract": p.abstract,
                    "title": p.title,
                    "published_ts": p.published,  # util.datetime_to_iso(p.published),
                    "embedding": json.dumps(p.embedding, separators=(",", ":"))
                    if p.embedding
                    else None,
                }

        def categories_to_insert():
            for p in papers:
                if p.categories:
                    for c in p.categories:
                        yield {"arxiv_id": p.arxiv_id, "category": c[:MAX_CATEGORY_LEN]}

        def authors_to_insert():
            for p in papers:
                if p.authors:
                    for a in p.authors:
                        yield {"arxiv_id": p.arxiv_id, "author": a[:MAX_AUTHOR_LEN]}

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                # Insert into ARXIV table
                self._bulk_insert(
                    table=Tables.ARXIV,
                    records=papers_to_insert(),
                    overwrite=True,
                    cursor=cur,
                    insert_cols=insert_cols,
                )

                # Insert into authors table
                self._bulk_insert(
                    table=Tables.ARXIV_AUTHORS,
                    records=authors_to_insert(),
                    overwrite=False,
                    cursor=cur,
                )

                # Insert into categories table
                self._bulk_insert(
                    table=Tables.ARXIV_CATEGORY,
                    records=categories_to_insert(),
                    overwrite=False,
                    cursor=cur,
                )

    def _list_index_map(self, lst):
        return {c: i for i, c in enumerate(lst)}

    def _row_to_arxiv_entity(self, row, col_idx) -> ArxivEntity:
        paper = arxiv.ArxivPaper(
            arxiv_id=row[col_idx["arxiv_id"]],
            title=row[col_idx["title"]],
            abstract=row[col_idx["abstract"]],
            published=row[col_idx["published_ts"]],
        )
        if "embedding" in col_idx:
            paper.embedding = row[col_idx["embedding"]]
        final = {
            col: row[col_idx[col]] for col in SOCIAL_ARXIV_COLUMNS if col in col_idx
        }
        final["paper"] = paper
        return ArxivEntity.parse_obj(final)

    def get_papers(
        self,
        arxiv_ids=None,
        ids_only=False,
        include_embeddings=False,
        required_null_fields=None,
        limit=None,
    ):
        """Queries the database for papers and returns the results.

        Args:
            arxiv_ids: Which arxiv IDs to query. None to query all.
            ids_only: Whether to only return a list of Arxiv IDs with no other
                information.
            include_embeddings: If not returning a list of arxiv IDs, whether to include
                embeddings in the response.
            required_null_fields: Only papers which have these fields as NULL are returned.
            limit: If specified, only the top `limit` most recent papers will be returned.
        """
        if ids_only and include_embeddings:
            raise ValueError("Cant set ids_only and include_embeddings at same time")
        results = []
        where = ""
        if required_null_fields:
            where = "WHERE " + " AND ".join(
                [f"{field} IS NULL" for field in required_null_fields]
            )
        if arxiv_ids:
            where += " AND arxiv_id IN ({0})".format(
                ",".join([f'"{arxiv_id}"' for arxiv_id in arxiv_ids])
            )
        if limit:
            where += f" ORDER BY published_ts DESC LIMIT {limit}"
        if ids_only:
            select = ["arxiv_id"]
        else:
            select = self.get_table_columns(Tables.ARXIV)
            if not include_embeddings:
                select.remove("embedding")

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {','.join(select)}
                    FROM {Tables.ARXIV}
                    {where}"""
                )
                if ids_only:
                    results = [row[0] for row in cur.fetchall()]
                else:
                    col_idx = self._list_index_map(select)
                    results = [
                        self._row_to_arxiv_entity(row, col_idx)
                        for row in cur.fetchall()
                    ]
        return results

    def get_similar_papers(
        self,
        embedding,
        lexical_query=None,
        top_k=10,
        start_date=None,
        end_date=None,
        require_social=False,
    ) -> List[SimilarityResult]:
        """Returns papers with embeddings similar to `embedding` according to
        the dot product (same as cosine similarity given normalized embeddings)

        Args:
            embedding: Embedding to query with as a list.
            top_k: Return the `top_k` most similar results.
            start_date: Earliest publication date.
            end_date: Latest publication date.
            require_social: Whether to require social engagements on results.
        """
        cols = self.get_table_columns(Tables.ARXIV)
        cols.remove("embedding")
        col_idx = self._list_index_map(cols)
        embedding = json.dumps(embedding, separators=(",", ":"))

        where_clause = []
        sql_args = []
        if start_date:
            start_date = util.datetime_to_date_str(start_date)
            where_clause.append(f"DATE(published_ts) >= '{start_date}'")
        if end_date:
            end_date = util.datetime_to_date_str(end_date)
            where_clause.append(f"DATE(published_ts) <= '{end_date}'")
        if require_social:
            where_clause.append(
                f"(likes > 0 OR retweets > 0 OR quotes > 0 OR replies > 0)"
            )
        if lexical_query:
            where_clause.append(
                f"text_search_vector @@ websearch_to_tsquery('english', %s)"
            )
            sql_args.append(lexical_query)

        if where_clause:
            where_clause_str = "WHERE " + " AND ".join(where_clause)
        else:
            where_clause_str = ""
        q = f"""
        SELECT {','.join([c for c in cols])}, 1 - (embedding <=> '{embedding}') AS similarity
        FROM {Tables.ARXIV}
        {where_clause_str}
        ORDER BY similarity DESC LIMIT {top_k}
        """
        results = []
        retries = 6
        while retries > 0:
            retries -= 1
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    try:
                        cur.execute(q, sql_args)
                    except psycopg.OperationalError:
                        print(
                            f"Database connection unsuccessful. {retries} tries left."
                        )
                        self._pool.check()
                        continue
                    for row in cur.fetchall():
                        full_result = self._row_to_arxiv_entity(row, col_idx)
                        results.append(
                            SimilarityResult(entity=full_result, similarity=row[-1])
                        )
                    break
        return results

    def get_latest_tweet_dt(self):
        """Returns the creation date of the latest tweet in the database."""
        q = "SELECT MAX(created_at) FROM tweet;"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(q)
                res = cur.fetchone()
                if not res:
                    return None
                return res[0]

    def update_arxiv_social_metrics(self):
        q = f"""
        SELECT at.arxiv_id, {','.join(['SUM(t.' + col + ') AS ' + col for col in SOCIAL_ARXIV_COLUMNS])}
        FROM {Tables.ARXIV_TWEET} at
        INNER JOIN {Tables.TWEET} t 
        ON at.tweet_id = t.tweet_id 
        GROUP BY at.arxiv_id
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(q)
                results = cur.fetchall()

                def papers_to_insert():
                    for res in results:
                        r = {"arxiv_id": res[0]}
                        for i, col in enumerate(SOCIAL_ARXIV_COLUMNS):
                            r[col] = res[i + 1]
                        yield r

                self._bulk_insert(
                    Tables.ARXIV,
                    papers_to_insert(),
                    cursor=cur,
                    insert_cols=SOCIAL_ARXIV_COLUMNS,
                    overwrite=True,
                )
