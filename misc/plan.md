# Plan for Arxiv Hype

## Overview
Arxiv Hype is a system for searching through the latest ML papers that are being discussed on Twitter. It is designed to track the popularity of papers and support a robust search interface powered by a customizable combination of embeddings, popularity, and exact match search.

## Requirements
The required capabilities are as follows:
* Pull the latest papers from Twitter. Track likes, replies, etc.
* Pull paper metadata from Arxiv about any papers found via Twitter.
* Store all Tweets pulled along with their engagement counts, date posted and tweet IDs. Do NOT store the tweet text.
* Store all Arxiv papers. For papers, we should store the title, abstract, and publication date.
* Store embeddings for all Arxiv papers. Could store in DB with papers to avoid a join, or store elsewhere (leaning towards elsewhere for flexibility?)
* We will need a way to easily compute the aggregate engagement metrics on each Arxiv paper.

## Files
* arxiv.py: Contains functions for pulling data from Arxiv.
* tweets.py: Contains functions for pulling Tweets via the Twitter API and parsing the responses.
* database.py: Contains functions for interacting with the database. No backend database code should exist outside of this.
* embeddings.py: Contains functions for computing embeddings of text.
* TODO: something for exact match
