from lib import database, hnews
import logging


def run(start_dt=None, num_results=100, order_by="date"):
    logging.info(f"Searching hacker news ordered by {order_by}")
    db = database.Database()

    # Search Twitter
    # TODO: Parameters like start date, number of tweets, etc.
    posts = hnews.search_for_arxiv(
        start_time=start_dt, num_results=num_results, order_by=order_by
    )

    # Add results to DB
    logging.info(f"Found {len(posts)} hnews posts.")
    db.insert_hnews(posts)
    db.update_arxiv_social_metrics(update_hnews=True)


if __name__ == "__main__":
    run()
