<script lang="ts">
	import axios from 'axios';
	import { apiUrl } from '$lib/Utils.svelte';

	let showModal = false;
	let modalTitle = '';
	let modalLinks = [];

	function toggleHNewsModal() {
		showModal = !showModal;
		if (!showModal) {
			modalLinks = [];
		}
	}

	export function getToggleHNewsModalFn(searchResult) {
		const fn = async function () {
			modalTitle = searchResult['entity']['paper']['title'];
			try {
				let response = await axios.get(apiUrl('hnews'), {
					params: {
						arxiv_id: searchResult['entity']['paper']['arxiv_id']
					}
				});
				let hnewsModalResults = response.data['data'];
				modalLinks = hnewsModalResults.map((res) => 'https://news.ycombinator.com/item?id=' + res);
			} catch (e) {
				console.log(e);
			}
			toggleHNewsModal();
		};
		return () => fn();
	}
</script>

<div class="tweet-modal">
	<dialog open style="visibility: {showModal ? 'visible' : 'hidden'}">
		<article style="width:100%">
			<header>
				<p
					on:click={toggleHNewsModal}
					on:keydown={toggleHNewsModal}
					aria-label="Close"
					class="close"
				/>
				{modalTitle}
			</header>
			<ul>
				{#each modalLinks as url, i}
					{#key url}
						<li><a href={url} target="_blank">{url}</a></li>
					{/key}
				{/each}
			</ul>
		</article>
	</dialog>
</div>

<style>
	.tweet-modal {
		height: 800px;
		display: block;
	}
</style>
