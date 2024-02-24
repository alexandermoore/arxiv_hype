<script lang="ts">
	import axios from 'axios';
	import { apiUrl } from '$lib/Utils.svelte';

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

	export function getToggleTweetModalFn(searchResult) {
		const fn = async function () {
			tweetModalTitle = searchResult['entity']['paper']['title'];
			try {
				let response = await axios.get(apiUrl('tweets'), {
					params: {
						arxiv_id: searchResult['entity']['paper']['arxiv_id']
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

	function handleTweetModelNextButton() {
		tweetModalStartIdx += tweetModalNumTweets;
		updateTweetModalFocusTweetsHtml();
	}
	function handleTweetModelPrevButton() {
		tweetModalStartIdx -= tweetModalNumTweets;
		updateTweetModalFocusTweetsHtml();
	}
</script>

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

<style>
	.tweet-modal {
		height: 800px;
		display: block;
	}
</style>
