<script lang="ts">
	import TweetModal from '$lib/TweetModal.svelte';
	import SearchResult from '$lib/SearchResult.svelte';
	import SearchBox from '$lib/SearchBox.svelte';
	import HNewsModal from '$lib/HNewsModal.svelte';
	import { apiUrl } from '$lib/Utils.svelte';
	import axios from 'axios';
	import { onMount } from 'svelte';

	let pageInfo = {
		title: 'ArXiv Hype',
		description: 'Search a selection of papers that have been mentioned on Twitter or HN.',
		github: 'https://www.github.com/alexanderm/arxiv_hype'
	};

	// for TweetModal
	let tweetModalInstance;
	let hnewsModalInstance;
	let searchResults = [];
	let lastSearchResult = Infinity;

	// const debounce = (fn: Function, ms = 300) => {
	// 	console.log('Entering');
	// 	let timeoutId: ReturnType<typeof setTimeout>;
	// 	return function (this: any, ...args: any[]) {
	// 		clearTimeout(timeoutId);
	// 		timeoutId = setTimeout(() => fn.apply(this, args), ms);
	// 	};
	// };

	// function getOpenHNewsUrlFn(i) {
	// 	const fn = async function () {
	// 		try {
	// 			let response = await axios.get(apiUrl('hnews'), {
	// 				params: {
	// 					arxiv_id: searchResults[i]['entity']['paper']['arxiv_id']
	// 				}
	// 			});
	// 			let hnewsIds = response.data['data'];
	// 			if (hnewsIds.length > 0) {
	// 				return 'https://news.ycombinator.com/item?id=' + hnewsIds[0];
	// 			}
	// 			return '#';
	// 		} catch (e) {
	// 			console.log(e);
	// 			return '#';
	// 		}
	// 	};
	// 	return () => {
	// 		fn().then((url) => {
	// 			if (url) {
	// 				window.open(url, '_blank')?.focus();
	// 			}
	// 		});
	// 	};
	// }

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
		<SearchBox
			bind:searchResults
			onSearchCallback={function () {
				lastSearchResult = 10;
			}}
		/>
		<!-- Search results display -->
		<div class="search-result-container">
			{#each searchResults.slice(0, lastSearchResult) as result, i}
				{#key result}
					<SearchResult {result} idx={i} {tweetModalInstance} {hnewsModalInstance} />{/key}
			{/each}
		</div>
		<button on:click={showMoreSearchResults} hidden={lastSearchResult >= searchResults.length}
			>Show More</button
		>
	</article>

	<TweetModal bind:this={tweetModalInstance} />
	<HNewsModal bind:this={hnewsModalInstance} />
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
