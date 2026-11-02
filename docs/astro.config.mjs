// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLinksValidator from 'starlight-links-validator';

export default defineConfig({
	site: 'https://docs.cyclix.dev',
	integrations: [
		starlight({
			title: 'Cyclix',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/ambitioushq/cyclix' }],
			sidebar: [
				{
					label: 'For people who run Cyclix',
					items: [
						{ label: 'Guides', items: [{ autogenerate: { directory: 'guides' } }] },
						{ label: 'Concepts', items: [{ autogenerate: { directory: 'concepts' } }] },
						{ label: 'Reference', items: [{ autogenerate: { directory: 'reference' } }] },
						{ label: 'Patterns', items: [{ autogenerate: { directory: 'patterns' } }] },
					],
				},
				{
					label: "For people who work on Cyclix's code",
					items: [
						{ label: 'Design', items: [{ autogenerate: { directory: 'design' } }] },
						{ label: 'Architecture decision records', items: [{ autogenerate: { directory: 'adr' } }] },
					],
				},
			],
			plugins: [starlightLinksValidator()],
		}),
	],
});
