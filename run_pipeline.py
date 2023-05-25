from pipeline import read_twitter, update_arxiv_data, update_arxiv_embeddings

if __name__ == "__main__":
    print("Handling Twitter")
    read_twitter.run()
    print("Handling arxiv data")
    update_arxiv_data.run()
    print("Handling arxiv embeddings")
    update_arxiv_embeddings.run()
