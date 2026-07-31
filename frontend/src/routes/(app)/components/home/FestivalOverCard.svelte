<script lang="ts">
	import SocialLinks from './SocialLinks.svelte';
</script>

<section
	aria-labelledby="festival-over-heading"
	class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7 dark:border-gray-800 dark:bg-gray-900"
>
	<h1
		id="festival-over-heading"
		class="font-display text-2xl leading-tight font-bold text-gray-900 sm:text-3xl dark:text-white"
	>
		До встречи!
	</h1>
	<!-- No past-tense address («спасибо, что был») — it would have to agree in gender,
		 which the copy cannot know. -->
	<p class="mt-2 max-w-prose text-sm leading-relaxed text-gray-600 sm:text-base dark:text-gray-300">
		ФАН ФАН 2026 завершён. Спасибо за этот день — программа остаётся в приложении, а новости о
		следующем фестивале появятся в наших соцсетях.
	</p>

	<div class="mt-5">
		<SocialLinks />
	</div>
</section>
