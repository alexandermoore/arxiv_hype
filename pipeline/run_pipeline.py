from pipeline import (
    read_twitter,
    read_hnews,
    update_arxiv_data,
    update_arxiv_embeddings,
)


def run(embedding_model=None, start_dt=None):
    # print("Handling Twitter")
    # read_twitter.run(start_dt=start_dt, max_results=50, num_time_blocks=3)
    print("Handling Hacker News")
    # API max is 1000 results
    # Fetch most recent
    read_hnews.run(num_results=1100, order_by="date", start_dt=start_dt)
    # Fetch most popular (could overlap recent heavily)
    read_hnews.run(num_results=1100, order_by="popularity", start_dt=start_dt)
    print("Handling arxiv data")
    update_arxiv_data.run()
    print("Handling arxiv embeddings")
    update_arxiv_embeddings.run(embedding_model=embedding_model)
    print("Done.")
