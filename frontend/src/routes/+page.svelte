<script lang="ts">
	import axios from 'axios';
	import { onMount } from 'svelte';
	import { fade, blur, slide } from 'svelte/transition';
	import Icon from '@iconify/svelte';

	let dt;
	let searchQuery: string = '';
	let lexicalSearchQuery: string = '';
	let searchResults = [];
	let lastSearchResult = Infinity;

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

	function toggleModal() {}

	function showMoreSearchResults() {
		const el = document.querySelector('#search-result-' + (lastSearchResult - 1));
		if (el) {
			// el.scrollIntoView({
			// 	behavior: 'smooth'
			// });
			const y = el.getBoundingClientRect().top + window.pageYOffset - 100;

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

		try {
			let response = await axios.get('http://localhost:8000/search', {
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
		console.log('md', maxDate);
	}

	function rawPopularityScore(result) {
		let likes = result['entity']['likes'] || 0;
		let retweets = result['entity']['retweets'] || 0;
		let quotes = result['entity']['quotes'] || 0;
		let impressions = result['entity']['quotes'] || 0;
		let replies = result['entity']['replies'] || 0;
		return Math.log(1 + likes + retweets * 2 + replies * 5 + quotes * 5 + impressions / 1000.0);
	}

	function decayedRecencyScore(date, maxDate) {
		const oneMonth = 30 * 24 * 3600 * 1000;
		const diff = maxDate - date;
		return Math.pow(0.5, diff / oneMonth);
	}

	function getSearchResultScore(result, maxSemanticScore, maxPopularityScore, maxDate) {
		let popularityScore = rawPopularityScore(result);
		let semanticSimilarity = result['similarity'];
		console.log({ semanticSimilarity, maxSemanticScore, popularityScore, maxPopularityScore });
		let published = new Date(result['entity']['paper']['published']).getTime();

		const wSemanticScore = (rankingSemantic * semanticSimilarity) / maxSemanticScore;
		const wPopularityScore = (rankingPopularity * popularityScore) / maxPopularityScore;
		const wRecencyScore = rankingRecency * decayedRecencyScore(published, maxDate);

		console.log({ wSemanticScore, wPopularityScore, wRecencyScore });
		return wSemanticScore + wPopularityScore + wRecencyScore;
	}

	function rankSearchResults() {
		console.log('ranking...');
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

<main class="container">
	<article>
		<!-- Header -->
		<header>
			<hgroup class="centered">
				<h1>ArXiv Hype</h1>
				<h2>Search a selection of papers that have been mentioned on Twitter.</h2>
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
			<a href="#" role="button" on:click={handleSearchWithButton}>Search</a>
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
							data-tooltip="Retrieving more papers allows for more ranking flexibility, but the page may run slower."
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
					<h6>These settings control how papers are ranked in your browser.</h6>
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
				<label for="ranking_lexical"
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
				</label>
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
						<div class="fade-text">
							{i + 1}.
							<a
								target="_blank"
								href={`http://www.arxiv.org/abs/${result['entity']['paper']['arxiv_id']}`}
								>{result['entity']['paper']['title']}</a
							>
							<p style="opacity:80%">
								<i>Submitted {formatDate(result['entity']['paper']['published'])}</i>
							</p>
							<p>{result['entity']['paper']['abstract']}</p>
						</div>
						<div class="grid">
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
						</div>
					</article>
				{/key}
			{/each}
		</div>
		<button on:click={showMoreSearchResults} hidden={lastSearchResult >= searchResults.length}
			>Show More</button
		>
	</article>
</main>

<style>
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
	.search-result {
		max-height: 400px;
		height: 400px;
		overflow: hidden;
	}
	.fade-text {
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