<script lang="ts">
	import axios from 'axios';
	import { apiUrl } from '$lib/Utils.svelte';

	export let onSearchCallback = function () {};

	// Readonly hack https://github.com/sveltejs/svelte/issues/7712#issuecomment-1642470141
	export let searchResults = [];
	let _searchResults = [];
	$: searchResults = _searchResults;

	let searchIsLoading = false;

	// refactor to dict
	let searchQuery: string = '';
	let lexicalSearchQuery: string = '';
	let exclLexicalSearchQuery: string = ''; // keywords to exclude

	let settings = {
		rankingSemantic: 100,
		rankingLexical: 0,
		rankingPopularity: 25,
		rankingRecency: 0,

		retrievalKeywordsMustAppear: false,
		retrievalExcludeKeywords: false,
		retrievalMustSocial: false,
		retrievalStartDate: undefined,
		retrievalEndDate: undefined,
		retrievalTopK: 50,
		lexicalSearchQuery: ''
	};
	export let showSummaries = false;

	// let rankingSemantic = 100;
	// let rankingLexical = 0;
	// let rankingPopularity = 25;
	// let rankingRecency = 0;

	// let retrievalKeywordsMustAppear = false;
	// let retrievalMustSocial = false;
	// let retrievalStartDate = undefined;
	// let retrievalEndDate = undefined;
	// let retrievalTopK = 50;

	function getSearchResultScore(result, maxSemanticScore, maxPopularityScore, maxDate) {
		let popularityScore = rawPopularityScore(result);
		let semanticSimilarity = result['similarity'];
		//console.log({ semanticSimilarity, maxSemanticScore, popularityScore, maxPopularityScore });
		let published = new Date(result['entity']['paper']['published']).getTime();
		const epsilon = 0.000001;
		const wSemanticScore =
			(settings.rankingSemantic * semanticSimilarity) / (epsilon + maxSemanticScore);
		const wPopularityScore =
			(settings.rankingPopularity * popularityScore) / (epsilon + maxPopularityScore);
		const wRecencyScore = settings.rankingRecency * decayedRecencyScore(published, maxDate);

		//console.log({ wSemanticScore, wPopularityScore, wRecencyScore });
		return wSemanticScore + wPopularityScore + wRecencyScore;
	}

	function computeMaxScores() {
		let maxSemanticScore = 0;
		let maxPopularityScore = 0;
		let maxDate = 0;
		_searchResults.forEach((result) => {
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
		return {
			semantic: maxSemanticScore,
			popularity: maxPopularityScore,
			date: maxDate
		};
	}

	function rawPopularityScore(result) {
		let likes = result['entity']['likes'] || 0;
		let retweets = result['entity']['retweets'] || 0;
		let quotes = result['entity']['quotes'] || 0;
		let impressions = result['entity']['impressions'] || 0;
		let replies = result['entity']['replies'] || 0;
		let score = Math.log(
			1 + likes + retweets * 2 + replies * 5 + quotes * 5 + impressions / 1000.0
		);
		return score;
	}

	function decayedRecencyScore(date, maxDate) {
		const oneMonth = 30 * 24 * 3600 * 1000;
		const diff = maxDate - date;
		return Math.pow(0.5, diff / (3 * oneMonth));
	}

	function rankSearchResults() {
		//lastSearchResult = 10;
		let maxScores = computeMaxScores();
		let resultScores = _searchResults.map((result) => {
			return {
				r: result,
				score: -getSearchResultScore(
					result,
					maxScores.semantic,
					maxScores.popularity,
					maxScores.date
				)
			};
		});
		resultScores.sort(function (a, b) {
			return a.score - b.score;
		});
		_searchResults = resultScores.map((resultScore) => resultScore['r']);
	}

	async function search(query: string) {
		let lexicalSearchQueryFinal;
		if (settings.retrievalKeywordsMustAppear) {
			lexicalSearchQueryFinal = lexicalSearchQuery || query;
		} else {
			lexicalSearchQueryFinal = undefined;
		}
		searchIsLoading = true;

		try {
			let response = await axios.get(apiUrl('search'), {
				params: {
					query: query,
					start_date: settings.retrievalStartDate,
					end_date: settings.retrievalEndDate,
					top_k: settings.retrievalTopK,
					require_social: settings.retrievalMustSocial,
					lexical_query: lexicalSearchQueryFinal,
					exclude_query: settings.retrievalExcludeKeywords ? exclLexicalSearchQuery : undefined
				}
			});
			_searchResults = response.data['data'];
			rankSearchResults();
			onSearchCallback();
		} catch (e) {
			console.log(e);
		}
		searchIsLoading = false;
	}

	function handleSearchWithButton() {
		search(searchQuery);
	}
	function handleSearchWithEnterKey(event: Event) {
		if (event['key'] === 'Enter') {
			search(searchQuery);
		}
	}
</script>

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
<!-- Whether to show summaries-->
<!-- <div>
	<label for="show_summaries">
		<input id="show_summaries" type="checkbox" bind:checked={showSummaries} />
		Show brief summaries instead of abstracts.
	</label>
</div>
<br /> -->

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
				<input
					id="retrieval_kw"
					type="checkbox"
					bind:checked={settings.retrievalKeywordsMustAppear}
				/>
				Query keywords must appear in paper title or abstract.
			</label>
			<div hidden={!settings.retrievalKeywordsMustAppear}>
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
			<label for="retrieval_excl_kw">
				<input
					id="retrieval_excl_kw"
					type="checkbox"
					bind:checked={settings.retrievalExcludeKeywords}
				/>
				Exclude specific keywords from results.
			</label>
			<div hidden={!settings.retrievalExcludeKeywords}>
				<label for="retrieval_excl_kw_query">
					Keywords to <span
						data-tooltip="Supports the use of quotes to create phrases, and 'OR' to match any of multiple words."
						>exclude</span
					>:
					<input
						style="width:50%"
						id="retrieval_excl_kw_query"
						bind:value={exclLexicalSearchQuery}
					/>
				</label>
			</div>
			<label for="retrieval_social">
				<input id="retrieval_social" type="checkbox" bind:checked={settings.retrievalMustSocial} />
				Papers must have at least one like, retweet or quote.
			</label>
			<label for="sdate"
				>Submission Date
				<input
					style="width:30%"
					type="date"
					id="sdate"
					name="sdate"
					bind:value={settings.retrievalStartDate}
				/>
				<span>to</span>
				<input
					style="width:30%"
					type="date"
					id="edate"
					name="edate"
					bind:value={settings.retrievalEndDate}
				/>
			</label>
			<label for="retrieval_topk"
				>Number of papers to <span
					data-tooltip="Retrieving more papers allows for more ranking flexibility, but the page may run more slowly."
					>retrieve</span
				>
				[<b>{settings.retrievalTopK}</b>]
				<input
					type="range"
					min="10"
					max="500"
					bind:value={settings.retrievalTopK}
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
				bind:value={settings.rankingSemantic}
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
				bind:value={settings.rankingPopularity}
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
				bind:value={settings.rankingRecency}
				on:change={rankSearchResults}
				id="ranking_recency"
				name="ranking_recency"
			/>
		</label>
	</article>
</details>

<style>
	.centered {
		text-align: center;
	}
	.search-box {
		width: 75%;
	}
</style>
