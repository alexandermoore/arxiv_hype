<script lang="ts">
	import axios from 'axios';
	import { onMount } from 'svelte';
	import { fade, blur, slide } from 'svelte/transition';
	import Icon from '@iconify/svelte';

	function apiUrl(endpoint) {
		return '/' + endpoint;
		//return 'http://localhost:8000/' + endpoint;
	}

	let pageInfo = {
		title: 'ArXiv Hype',
		description: 'Search a selection of papers that have been mentioned on Twitter.',
		github: 'https://www.github.com/alexanderm/arxiv_hype'
	};

	let dt;
	let searchQuery: string = '';
	let lexicalSearchQuery: string = '';
	let searchResults = [];
	let lastSearchResult = Infinity;
	let searchIsLoading = false;

	let rankingSemantic = 100;
	let rankingLexical = 0;
	let rankingPopularity = 25;
	let rankingRecency = 0;

	let retrievalKeywordsMustAppear = false;
	let retrievalMustSocial = false;
	let retrievalStartDate = undefined;
	let retrievalEndDate = undefined;
	let retrievalTopK = 50;

	let maxSemanticScore = 0;
	let maxPopularityScore = 0;
	let maxDate: number = 0;
	let minDate: number = Infinity;

	// const debounce = (fn: Function, ms = 300) => {
	// 	console.log('Entering');
	// 	let timeoutId: ReturnType<typeof setTimeout>;
	// 	return function (this: any, ...args: any[]) {
	// 		clearTimeout(timeoutId);
	// 		timeoutId = setTimeout(() => fn.apply(this, args), ms);
	// 	};
	// };

	let showTweetModal = false;
	let tweetModalTweets = [];
	let tweetModalStartIdx = 0;
	let tweetModalNumTweets = 2;
	let tweetModalFocusTweetsHtml = [];
	let tweetModalTitle = '';
	function toggleTweetModal() {
		showTweetModal = !showTweetModal;
		if (!showTweetModal) {
			tweetModalTweets = [];
			tweetModalFocusTweetsHtml = [];
		}
	}

	// import jsonp from 'jsonp';

	// async function getEmbeddedTweetHtml(tweetId) {
	// 	try {
	// 		let response = await axios.get(apiUrl('tweets'), {
	// 			params: {
	// 				embed_tweets: true
	// 			}
	// 		});
	// 		return response['dat'];
	// 	} catch (e) {
	// 		console.log(e);
	// 	}
	// 	return 'Nada!';

	// 	// jsonp(
	// 	// 	'https://publish.twitter.com/oembed?url=https://twitter.com/x/status/' + tweetId,
	// 	// 	null,
	// 	// 	(err, data) => {
	// 	// 		if (err) {
	// 	// 			console.error(err.message);
	// 	// 		} else {
	// 	// 			console.log(data);
	// 	// 		}
	// 	// 	}
	// 	// );
	// }

	async function updateTweetModalFocusTweetsHtml() {
		let tweetIds = tweetModalTweets.slice(
			tweetModalStartIdx,
			tweetModalStartIdx + tweetModalNumTweets
		);
		try {
			//console.log({ tweetIds, tweetModalTweets });
			let response = await axios.get(apiUrl('embed_tweets'), {
				params: {
					tweet_ids: tweetIds
				}
			});
			tweetModalFocusTweetsHtml = response.data['data'];
		} catch (e) {
			console.log(e);
		}
	}
	function getToggleTweetModalFn(i) {
		const fn = async function () {
			tweetModalTitle = searchResults[i]['entity']['paper']['title'];
			try {
				let response = await axios.get(apiUrl('tweets'), {
					params: {
						arxiv_id: searchResults[i]['entity']['paper']['arxiv_id']
					}
				});
				tweetModalTweets = response.data['data'];
			} catch (e) {
				console.log(e);
				tweetModalTweets = [];
			}
			tweetModalStartIdx = 0;
			updateTweetModalFocusTweetsHtml();
			toggleTweetModal();
		};
		return () => fn();
	}

	function getExpandSearchResultFn(i) {
		return () => {
			let searchResult = document.querySelector('#search-result-' + i);
			let searchResultText = document.querySelector('#search-result-text-' + i);
			if (!searchResult || !searchResultText) {
				return;
			}
			if (!searchResult.classList.contains('search-result')) {
				searchResult.classList.add('search-result');
				searchResultText.classList.add('fade-text');
			} else {
				searchResult.classList.remove('search-result');
				searchResultText.classList.remove('fade-text');
			}
		};
	}

	function handleTweetModelNextButton() {
		tweetModalStartIdx += tweetModalNumTweets;
		updateTweetModalFocusTweetsHtml();
	}
	function handleTweetModelPrevButton() {
		tweetModalStartIdx -= tweetModalNumTweets;
		updateTweetModalFocusTweetsHtml();
	}

	function showMoreSearchResults() {
		const el = document.querySelector('#search-result-' + (lastSearchResult - 1));
		if (el) {
			// el.scrollIntoView({
			// 	behavior: 'smooth'
			// });
			const y = el.getBoundingClientRect().top + window.pageYOffset; // + 200;

			window.scrollTo({ top: y, behavior: 'smooth' });
		}
		lastSearchResult += 20;
	}

	async function search(query: string) {
		if (query.trim() == '') {
			return;
		}
		let lexicalSearchQueryFinal;
		if (retrievalKeywordsMustAppear) {
			lexicalSearchQueryFinal = lexicalSearchQuery || query;
		} else {
			lexicalSearchQueryFinal = undefined;
		}
		searchIsLoading = true;
		try {
			let response = await axios.get(apiUrl('search'), {
				params: {
					query: query,
					start_date: retrievalStartDate,
					end_date: retrievalEndDate,
					top_k: retrievalTopK,
					require_social: retrievalMustSocial,
					lexical_query: lexicalSearchQueryFinal
				}
			});
			searchResults = response.data['data'];
			computeMaxScores();
			rankSearchResults();
		} catch (e) {
			console.log(e);
		}
		searchIsLoading = false;
	}

	function computeMaxScores() {
		maxSemanticScore = 0;
		maxPopularityScore = 0;
		maxDate = 0;
		searchResults.forEach((result) => {
			if (result['similarity'] > maxSemanticScore) {
				maxSemanticScore = result['similarity'];
			}
			const popScore = rawPopularityScore(result);
			if (popScore > maxPopularityScore) {
				maxPopularityScore = popScore;
			}
			const published = new Date(result['entity']['paper']['published']).getTime();
			if (published > maxDate) {
				maxDate = published;
			}
		});
	}

	function rawPopularityScore(result) {
		let likes = result['entity']['likes'] || 0;
		let retweets = result['entity']['retweets'] || 0;
		let quotes = result['entity']['quotes'] || 0;
		let impressions = result['entity']['impressions'] || 0;
		let replies = result['entity']['replies'] || 0;
		return Math.log(1 + likes + retweets * 2 + replies * 5 + quotes * 5 + impressions / 1000.0);
	}

	function decayedRecencyScore(date, maxDate) {
		const oneMonth = 30 * 24 * 3600 * 1000;
		const diff = maxDate - date;
		return Math.pow(0.5, diff / (3 * oneMonth));
	}

	function getSearchResultScore(result, maxSemanticScore, maxPopularityScore, maxDate) {
		let popularityScore = rawPopularityScore(result);
		let semanticSimilarity = result['similarity'];
		//console.log({ semanticSimilarity, maxSemanticScore, popularityScore, maxPopularityScore });
		let published = new Date(result['entity']['paper']['published']).getTime();

		const wSemanticScore = (rankingSemantic * semanticSimilarity) / maxSemanticScore;
		const wPopularityScore = (rankingPopularity * popularityScore) / maxPopularityScore;
		const wRecencyScore = rankingRecency * decayedRecencyScore(published, maxDate);

		//console.log({ wSemanticScore, wPopularityScore, wRecencyScore });
		return wSemanticScore + wPopularityScore + wRecencyScore;
	}

	function rankSearchResults() {
		lastSearchResult = 10;
		let resultScores = searchResults.map((result) => {
			return {
				r: result,
				score: -getSearchResultScore(result, maxSemanticScore, maxPopularityScore, maxDate)
			};
		});
		resultScores.sort(function (a, b) {
			return a.score - b.score;
		});
		searchResults = resultScores.map((resultScore) => resultScore['r']);
	}

	function handleSearchWithButton() {
		search(searchQuery);
	}
	function handleSearchWithEnterKey(event: Event) {
		if (event['key'] === 'Enter') {
			search(searchQuery);
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };
		return date.toLocaleDateString('en-US', options);
	}
</script>

<svelte:head>
	<title>{pageInfo.title}</title>
</svelte:head>

<main class="container">
	<article>
		<!-- Header -->
		<header>
			<hgroup class="centered">
				<h1>{pageInfo.title}</h1>
				<h2>{pageInfo.description}</h2>
			</hgroup>
		</header>
		<div class="centered">
			<input
				on:keydown={handleSearchWithEnterKey}
				class="search-box"
				type="search"
				placeholder="Search..."
				bind:value={searchQuery}
			/>
			<a
				href="#"
				role="button"
				on:click={handleSearchWithButton}
				aria-busy={searchIsLoading ? 'true' : 'false'}>Search</a
			>
		</div>

		<!-- Advanced search settings -->
		<details>
			<summary class:centered={searchQuery == 'hello'}>Advanced search settings</summary>
			<article>
				<hgroup>
					<h5>Retrieval Settings</h5>
					<h6>These settings control how papers are retrieved from the database.</h6>
				</hgroup>
				<!-- Checkboxes -->
				<fieldset>
					<label for="retrieval_kw">
						<input id="retrieval_kw" type="checkbox" bind:checked={retrievalKeywordsMustAppear} />
						Query keywords must appear in paper title or abstract.
					</label>
					<div hidden={!retrievalKeywordsMustAppear}>
						<label for="retrieval_kw_query">
							Query to use for keyword <span
								data-tooltip="Supports the use of quotes to create phrases, and 'OR' to match any of multiple words."
								>matching</span
							>:
							<input
								style="width:50%"
								id="retrieval_kw_query"
								placeholder={searchQuery}
								bind:value={lexicalSearchQuery}
							/>
						</label>
					</div>
					<label for="retrieval_social">
						<input id="retrieval_social" type="checkbox" bind:checked={retrievalMustSocial} />
						Papers must have at least one like, retweet or quote.
					</label>
					<label for="sdate"
						>Submission Date
						<input
							style="width:30%"
							type="date"
							id="sdate"
							name="sdate"
							bind:value={retrievalStartDate}
						/>
						<span>to</span>
						<input
							style="width:30%"
							type="date"
							id="edate"
							name="edate"
							bind:value={retrievalEndDate}
						/>
					</label>
					<label for="retrieval_topk"
						>Number of papers to <span
							data-tooltip="Retrieving more papers allows for more ranking flexibility, but the page may run more slowly."
							>retrieve</span
						>
						[<b>{retrievalTopK}</b>]
						<input
							type="range"
							min="10"
							max="500"
							bind:value={retrievalTopK}
							id="retrieval_topk"
							name="retrieval_topk"
						/>
					</label>
				</fieldset>
			</article>
			<article>
				<hgroup>
					<h5>Ranking Settings</h5>
					<h6>These settings control how papers are ranked on this page.</h6>
				</hgroup>
				<label for="ranking_semantic"
					>Semantic/meaning match importance
					<input
						type="range"
						min="0"
						max="100"
						bind:value={rankingSemantic}
						on:change={rankSearchResults}
						id="ranking_semantic"
						name="ranking_semantic"
					/>
				</label>
				<!-- <label for="ranking_lexical"
					>Keyword match importance
					<input
						type="range"
						min="0"
						max="100"
						bind:value={rankingLexical}
						on:change={rankSearchResults}
						id="ranking_lexical"
						name="ranking_lexical"
						disabled
					/>
				</label> -->
				<label for="ranking_popularity"
					>Popularity importance
					<input
						type="range"
						min="0"
						max="100"
						bind:value={rankingPopularity}
						on:change={rankSearchResults}
						id="ranking_popularity"
						name="ranking_popularity"
					/>
				</label>
				<label for="ranking_recency"
					>Recency importance
					<input
						type="range"
						min="0"
						max="100"
						bind:value={rankingRecency}
						on:change={rankSearchResults}
						id="ranking_recency"
						name="ranking_recency"
					/>
				</label>
			</article>
		</details>
		<!-- Search results display -->
		<div class="search-result-container">
			{#each searchResults.slice(0, lastSearchResult) as result, i}
				{#key result}
					<article
						id="search-result-{i}"
						class="search-result"
						transition:fade={{ duration: 200, delay: i * 10 }}
					>
						<div id="search-result-text-{i}" class="fade-text">
							{i + 1}.
							<a
								target="_blank"
								href={`http://www.arxiv.org/abs/${result['entity']['paper']['arxiv_id']}`}
								>{result['entity']['paper']['title']}</a
							>
							<p style="opacity:80%">
								<i>Submitted {formatDate(result['entity']['paper']['published'])}</i>
							</p>
							<div on:keydown={getExpandSearchResultFn(i)} on:click={getExpandSearchResultFn(i)}>
								{result['entity']['paper']['abstract']}
							</div>
						</div>
						<div class="grid">
							<!-- Twitter social metrics -->
							{#if result['entity']['likes'] !== null}
								<div>
									<Icon class="social-icon" icon="icon-park-outline:like" />
									{result['entity']['likes']}
								</div>
								<div>
									<Icon class="social-icon" icon="la:retweet" />
									{result['entity']['retweets']}
								</div>
								<div>
									<Icon class="social-icon" icon="radix-icons:chat-bubble" />
									{result['entity']['replies']}
								</div>
								<div>
									<a
										class="view-tweets-icon"
										on:keydown={getToggleTweetModalFn(i)}
										on:click={getToggleTweetModalFn(i)}
									>
										<Icon class="social-icon" icon="basil:twitter-outline" />
									</a>
								</div>
							{/if}
							<!-- HackerNews social metrics -->
							{#if result['entity']['points'] !== null}
								<div>
									<Icon class="social-icon" icon="bx:upvote" />
									{result['entity']['points']}
								</div>
							{/if}
							{#if result['entity']['num_comments'] !== null}
								<div>
									<Icon class="social-icon" icon="material-symbols:comment-outline" />
									{result['entity']['num_comments']}
								</div>
							{/if}
						</div>
					</article>
				{/key}
			{/each}
		</div>
		<button on:click={showMoreSearchResults} hidden={lastSearchResult >= searchResults.length}
			>Show More</button
		>
	</article>

	<div class="tweet-modal">
		<dialog open style="visibility: {showTweetModal ? 'visible' : 'hidden'}">
			<article style="width:100%">
				<header>
					<p
						on:click={toggleTweetModal}
						on:keydown={toggleTweetModal}
						aria-label="Close"
						class="close"
					/>
					{tweetModalTitle}
				</header>
				{#each tweetModalFocusTweetsHtml as tweetHtml, i}
					{#key tweetHtml}
						<div>
							{@html tweetHtml}
						</div>
					{/key}
				{/each}
				<div class="grid">
					<div class="centered">
						<button
							on:click={handleTweetModelPrevButton}
							class="secondary"
							disabled={tweetModalStartIdx == 0}>Prev</button
						>
					</div>
					<div class="centered">
						<button
							on:click={handleTweetModelNextButton}
							class="secondary"
							disabled={tweetModalStartIdx + tweetModalNumTweets >= tweetModalTweets.length}
							>Next</button
						>
					</div>
				</div>
				<div class="centered">
					<p>
						[{1 + Math.floor(tweetModalStartIdx / tweetModalNumTweets)} / {Math.ceil(
							tweetModalTweets.length / tweetModalNumTweets
						)}]
					</p>
				</div>
			</article>
		</dialog>
	</div>
</main>

<style>
	.tweet-modal {
		height: 800px;
		display: block;
	}
	.view-tweets-icon {
		color: #888888;
	}
	.view-tweets-icon:hover {
		color: #1da1f2;
	}
	.search-result-container {
		overflow: hidden;
	}
	div :global(.social-icon) {
		font-size: 24px;
	}
	.centered {
		text-align: center;
	}
	.search-box {
		width: 75%;
	}
	:global(.search-result) {
		max-height: 400px;
		height: 400px;
		overflow: hidden;
	}
	:global(.fade-text) {
		-webkit-mask-image: linear-gradient(to bottom, black 80%, transparent 99%);
		mask-image: linear-gradient(to bottom, black 80%, transparent 99%);
		max-height: 100%;
	}

	/* summary::before {
		background-image: var(--icon-chevron);
	}
	summary::after {
		background-image: none;
	} */

	/* Pink Light scheme (Default) */
	/* Can be forced with data-theme="light" */
	/* [data-theme='light'],
	:root:not([data-theme='dark']) {
		--primary: var(--main-color);
		--primary-hover: #c2185b;
		--primary-focus: rgba(216, 27, 96, 0.125);
		--primary-inverse: #fff;
	} */

	/* Pink Dark scheme (Auto) */
	/* Automatically enabled if user has Dark mode enabled */
	/* @media only screen and (prefers-color-scheme: dark) {
		:root:not([data-theme]) {
			--primary: var(--main-color);
			--primary-hover: #e91e63;
			--primary-focus: rgba(216, 27, 96, 0.25);
			--primary-inverse: #fff;
		}
	} */

	/* Pink Dark scheme (Forced) */
	/* Enabled if forced with data-theme="dark" */
	/* [data-theme='dark'] {
		--primary: var(--main-color);
		--primary-hover: #e91e63;
		--primary-focus: rgba(216, 27, 96, 0.25);
		--primary-inverse: #fff;
	} */

	/* Pink (Common styles) */
	/* :root {
		--main-color: #00b61e;
		--form-element-active-border-color: var(--primary);
		--form-element-focus-color: var(--primary-focus);
		--switch-color: var(--primary-inverse);
		--switch-checked-background-color: var(--primary);
	} */
</style>
