# Note: the module name is psycopg, not psycopg3
import psycopg
from lib import tweets, arxiv, util
from typing import List, Dict, Any, Iterable
from enum import Enum
from psycopg_pool import ConnectionPool
import uuid

class Tables(str, Enum):
    ARXIV = "Arxiv"
    ARXIV_AUTHORS = "ArxivAuthor"
    ARXIV_CATEGORY = "ArxivCategory"
    TWEET = "Tweet"
    ARXIV_TWEET = "ArxivTweet"

# TABLE_SCHEMA = {
#     Tables.ARXIV: [
#         ("arxiv_id", "VARCHAR(12)"),
#         ("title", "TEXT"),
#         ("abstract", "TEXT"),
#         ("published_dt", "DATETIME")],
#     Tables.TWEETS: [
#         ("tweet_id", "BIGINT"),
#         ("likes", "INTEGER"),
#         ("retweets", "INTEGER"),
#         ("replies", "INTEGER"),
#         ("quotes", "INTEGER"),
#         ("impressions", "INTEGER")],
#     Tables.ARXIV_AUTHORS = [
#         ("arxiv_id", "VARCHAR(12)"),
#         ("")
#     ]
# }



class Database():
    def __init__(self):
        with open("private/postgres_string.txt", "r") as f:
            self.POSTGRES_STR = f.read().strip()
        self._pool = ConnectionPool(self.POSTGRES_STR)
        self._table_columns = {}

    def create_tables(self):
        q = []
        # Arxiv Table Query
        q.append(f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV} (
            arxiv_id VARCHAR(12),
            title TEXT,
            abstract TEXT,
            published_ts TIMESTAMP,

            PRIMARY KEY (arxiv_id)
        );
        """)

        # Tweet Table Query
        q.append(f"""
        CREATE TABLE IF NOT EXISTS {Tables.TWEET} (
            tweet_id BIGINT,
            likes INTEGER,
            retweets INTEGER,
            replies INTEGER,
            quotes INTEGER,
            impressions INTEGER,

            PRIMARY KEY (tweet_id)
        );
        """)

        # Arxiv Authors Table Query
        q.append(f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV_AUTHORS} (
            arxiv_id VARCHAR(12),
            author VARCHAR(50),

            PRIMARY KEY (arxiv_id, author),

            CONSTRAINT fk_author_arxiv
                FOREIGN KEY (arxiv_id)
                REFERENCES {Tables.ARXIV}(arxiv_id)
        );
        """)

        # Arxiv Category Table Query
        q.append(f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV_CATEGORY} (
            arxiv_id VARCHAR(12),
            category VARCHAR(16),

            PRIMARY KEY (arxiv_id, category),

            CONSTRAINT fk_category_arxiv
                FOREIGN KEY (arxiv_id)
                REFERENCES {Tables.ARXIV}(arxiv_id)
        );
        """)

        # Arxiv Tweet Table Query
        q.append(f"""
        CREATE TABLE IF NOT EXISTS {Tables.ARXIV_TWEET} (
            arxiv_id VARCHAR(12),
            tweet_id BIGINT,

            PRIMARY KEY (arxiv_id, tweet_id),

            CONSTRAINT fk_category_arxiv
                FOREIGN KEY (arxiv_id)
                REFERENCES {Tables.ARXIV}(arxiv_id),

            CONSTRAINT fk_category_tweet
                FOREIGN KEY (tweet_id)
                REFERENCES {Tables.TWEET}(tweet_id)
        );
        """)

        with self._pool.connection() as conn:
            for t in q:
                conn.execute(t)
            conn.commit()

    def delete_tables(self):
        with self._pool.connection() as conn:
            for t in Tables:
                conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")


    def get_table_columns(self, table):
        if table not in self._table_columns:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT * FROM {table} LIMIT 0")
                    self._table_columns[table] = [desc[0] for desc in cur.description]
        return self._table_columns[table]

    def _format_record_to_tuple(self, record, cols):
        return tuple([record.get(c) for c in cols])

    def bulk_insert(
            self,
            table,
            id_cols,
            records: Iterable[Dict[str, Any]],
            insert_cols=None,
            overwrite=True
    ):
        with self._pool.connection() as conn:
            with conn.cursor() as cursor:
                self._bulk_insert(table, id_cols, records, insert_cols=insert_cols, overwrite=overwrite, cursor=cursor)
        
    def _bulk_insert(
            self,
            table,
            id_cols,
            records: Iterable[Dict[str, Any]],
            insert_cols=None,
            overwrite=True,
            cursor=None):
        temp_table_id = f"{table}_tmp_{str(uuid.uuid4())[:6]}"

        insert_cols = self.get_table_columns(table) if insert_cols is None else insert_cols
        insert_cols = list(set(insert_cols).union(id_cols))
        insert_cols_str = ','.join(insert_cols)
        
        cur = cursor

        cur.execute(f"""
            CREATE TEMPORARY TABLE {temp_table_id} 
            ON COMMIT DROP
            AS SELECT {insert_cols_str} FROM {table} LIMIT 0
            """)
        with cur.copy(f"COPY {temp_table_id} FROM STDIN") as copy:
            for record in records:
                record = self._format_record_to_tuple(record, insert_cols)
                copy.write_row(record)

        if overwrite:
            # Update inserted columns, leave others alone
            update_set = ",".join([f"{c}=excluded.{c}" for c in insert_cols if c not in id_cols])
            conflict = f"DO UPDATE SET {update_set}"
        else:
            conflict = "DO NOTHING"
        cur.execute(f"""
        INSERT INTO {table}({insert_cols_str})
        SELECT {insert_cols_str} FROM {temp_table_id}
        ON CONFLICT ({','.join(id_cols)}) {conflict}
        """)
    
    def insert_tweets(self, tweets: List[tweets.ArxivTweet]):
        def tweets_to_insert():
            for t in tweets:
                tweet = {
                    "tweet_id": t.tweet_id,
                    "likes": t.likes,
                    "retweets": t.retweets,
                    "replies": t.replies,
                    "quotes": t.quotes,
                    "impressions": t.impressions
                }
                yield tweet

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
                    Tables.TWEET,
                    ("tweet_id",),
                    tweets_to_insert(),
                    overwrite=True,
                    cursor=cur)
                # Delete edits (TODO)

                # Delete arxiv posts referenced by edits? (no it's fine)

                # Insert blank papers into arxiv table if any not present.
                # We can handle arxiv papers later.
                self._bulk_insert(
                    Tables.ARXIV,
                    ("arxiv_id",),
                    papers_to_insert(),
                    overwrite=False,
                    cursor=cur
                )

                # Update reference table
                self._bulk_insert(
                    Tables.ARXIV_TWEET,
                    ("arxiv_id", "tweet_id"),
                    references_to_insert(),
                    overwrite=False,
                    cursor=cur
                )

    def insert_papers(self, papers: List[arxiv.ArxivPaper]):
        def papers_to_insert():
            for p in papers:
                tweet = {
                    "arxiv_id": p.arxiv_id,
                    "abstract": p.abstract,
                    "title": p.title,
                    "published_ts": util.datetime_to_iso(p.published)
                }
                yield tweet
        
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                # Insert papers
                self._bulk_upsert(
                    Tables.TWEET,
                    ("arxiv_id",),
                    papers_to_insert(),
                    cursor=cur)

    def get_matchinig_papers(self, query, top_k, rank_method=None):
        # rank_method can be semantic or lexical, create an enum for this.
        # Maybe return a list of ArxivPaper
        pass