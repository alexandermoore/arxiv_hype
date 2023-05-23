<script lang="ts">
	import axios from 'axios';
	import { onMount } from 'svelte';
	import { fade, blur, slide } from 'svelte/transition';

	let dt;
	let searchQuery: string = '';
	let searchResults = [];

	async function search(query: string) {
		if (query.trim() == '') {
			return;
		}
		try {
			let response = await axios.get('http://localhost:8000/search', {
				params: { query: query }
			});
			searchResults = response.data;
		} catch (e) {
			console.log(e);
		}
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
						<input id="retrieval_kw" type="checkbox" />
						Query keywords must appear in paper title or abstract.
					</label>
					<label for="retrieval_social">
						<input id="retrieval_kw" type="checkbox" />
						Papers must have at least one like, retweet or quote.
					</label>
					<label for="sdate"
						>Submission Date
						<input style="width:30%" type="date" id="sdate" name="sdate" />
						<span>to</span>
						<input style="width:30%" type="date" id="edate" name="edate" />
					</label>
				</fieldset>
			</article>
			<article>
				<hgroup>
					<h5>Ranking Settings</h5>
					<h6>These settings control how papers are ranked in your browser.</h6>
				</hgroup>
				<label for="ranking_lexical"
					>Semantic/meaning match importance
					<input
						type="range"
						min="0"
						max="100"
						value="50"
						id="ranking_lexical"
						name="ranking_lexical"
					/>
				</label>
				<label for="ranking_semantic"
					>Keyword match importance
					<input
						type="range"
						min="0"
						max="100"
						value="50"
						id="ranking_semantic"
						name="ranking_semantic"
					/>
				</label>
				<label for="ranking_popularity"
					>Popularity importance
					<input
						type="range"
						min="0"
						max="100"
						value="50"
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
						value="50"
						id="ranking_recency"
						name="ranking_recency"
					/>
				</label>
			</article>
		</details>

		<!-- Search results display -->
		{#each searchResults as result, i}
			{#key result}
				<article class="search-result" transition:slide={{ duration: 200, delay: i * 10 }}>
					<div class="fade-text">
						<a target="_blank" href={`http://www.arxiv.org/abs/${result[0]['arxiv_id']}`}
							>{result[0]['title']}</a
						>
						<p style="opacity:80%"><i>Submitted {formatDate(result[0]['published'])}</i></p>
						<p>{result[0]['abstract']}</p>
					</div>
				</article>
			{/key}
		{/each}
	</article>
	<!-- Date -->
	<!-- <label for="date"
		>Date
		<input type="date" id="date" name="date" bind:value={dt} />
		<div>{dt}</div>
		<div>{searchQuery}</div>
	</label> -->
</main>

<style>
	.centered {
		text-align: center;
	}
	.search-box {
		width: auto;
	}
	.search-result {
		max-height: 400px;
		height: 400px;
		overflow: hidden;
	}
	.fade-text {
		-webkit-mask-image: linear-gradient(to bottom, black 60%, transparent 90%);
		mask-image: linear-gradient(to bottom, black 60%, transparent 90%);
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
