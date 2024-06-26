<script lang="ts">
	import { fade, blur, slide } from 'svelte/transition';
	import Icon from '@iconify/svelte';
	import { component_subscribe } from 'svelte/internal';

	export let result;
	export let idx;
	export let tweetModalInstance;
	export let hnewsModalInstance;
	export let showSummary = false;

	let resultId = 'search-result-' + idx;
	let resultTextId = 'search-result-text-' + idx;

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };
		return date.toLocaleDateString('en-US', options);
	}

	function expandSearchResultFn() {
		let searchResult = document.querySelector('#' + resultId);
		let searchResultText = document.querySelector('#' + resultTextId);
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
	}

	function getHTML(): string {
		function trimString(s, startswith) {
			if (s.startsWith(startswith)) {
				s = s.slice(startswith.length).trim();
				s = s.charAt(0).toUpperCase() + s.slice(1);
				return s;
			}
			return s;
		}
		if (showSummary) {
			let summary = result['entity']['paper']['summary'];
			console.log(result);
			if (summary != null) {
				summary = JSON.parse(summary);
				let contrib = summary['contribution'];
				contrib = trimString(contrib, 'This paper');
				contrib = trimString(contrib, 'The paper');
				return contrib;
				// return (
				// 	'<ul><li>' +
				// 	summary['motivation'] +
				// 	'</li><li>' +
				// 	summary['contribution'] +
				// 	'</li><li>' +
				// 	summary['result'] +
				// 	'</li>'
				// );
			}
		}
		return result['entity']['paper']['abstract'];
	}
</script>

<article
	id={resultId}
	class:search-result={!showSummary}
	transition:fade={{ duration: 200, delay: idx * 10 }}
>
	<div id={resultTextId} class:fade-text={!showSummary}>
		{idx + 1}.
		<a target="_blank" href={`http://www.arxiv.org/abs/${result['entity']['paper']['arxiv_id']}`}
			>{result['entity']['paper']['title']}</a
		>
		<p style="opacity:80%">
			<i>Submitted {formatDate(result['entity']['paper']['published'])}</i>
		</p>
		<div on:keydown={expandSearchResultFn} on:click={expandSearchResultFn}>
			{#if showSummary}
				{@html getHTML()}
			{:else}
				{@html getHTML()}
			{/if}
			<!-- {@html getHTML()} -->
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
					on:keydown={tweetModalInstance.getToggleTweetModalFn(result)}
					on:click={tweetModalInstance.getToggleTweetModalFn(result)}
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
		<!-- TODO: Fix this to open the new window properly. -->
		{#if result['entity']['num_comments'] !== null}
			<div>
				<a
					class="view-hnews-icon"
					on:keydown={hnewsModalInstance.getToggleHNewsModalFn(result)}
					on:click={hnewsModalInstance.getToggleHNewsModalFn(result)}
				>
					<Icon class="social-icon" icon="la:hacker-news-square" />
				</a>
			</div>
		{/if}
	</div>
</article>

<style>
	.fade-text {
		-webkit-mask-image: linear-gradient(to bottom, black 80%, transparent 99%);
		mask-image: linear-gradient(to bottom, black 80%, transparent 99%);
		max-height: 100%;
	}
	/* :global(.search-result) {*/
	.search-result {
		max-height: 400px;
		height: 400px;
		overflow: hidden;
	}
	.view-tweets-icon {
		color: #888888;
	}
	.view-tweets-icon:hover {
		color: #1da1f2;
	}
	.view-hnews-icon {
		color: #888888;
	}
	.view-hnews-icon:hover {
		color: #f36a0f;
	}
</style>
