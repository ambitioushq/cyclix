// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLinksValidator from 'starlight-links-validator';
import { satteri } from '@astrojs/markdown-satteri';
import { docsFolderPlugin } from './src/docs.mjs';

export default defineConfig({
	markdown: { processor: satteri({ mdastPlugins: [docsFolderPlugin] }) },
	integrations: [
		starlight({
			title: 'Cyclix',
			// Starlight adds heading anchors and its other Markdown features only to pages
			// in its own folder and in the folders listed here.
			markdown: { processedDirs: ['../docs'] },
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/ambitioushq/cyclix' }],
			// Starlight matches a page to a group by the page's file path from site/, so each
			// directory names a folder under ../docs.
			sidebar: [
				{
					label: 'For people who run Cyclix',
					items: [{ autogenerate: { directory: '../docs/concepts' } }, { autogenerate: { directory: '../docs/reference' } }],
				},
				{ label: "For people who work on Cyclix's code", items: [{ autogenerate: { directory: '../docs/design' } }] },
				{ label: 'The decisions', items: [{ autogenerate: { directory: '../docs/adr' } }] },
			],
			plugins: [
				starlightLinksValidator({
					// The validator cannot find the home page, as the comment in src/docs.mjs
					// explains, so it skips links to it. tests/harness/docs.feature checks them.
					exclude: ['/', '/#*'],
				}),
			],
		}),
	],
});
