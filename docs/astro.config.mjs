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
					items: [{ autogenerate: { directory: 'concepts' } }, { autogenerate: { directory: 'reference' } }],
				},
				{ label: "For people who work on Cyclix's code", items: [{ autogenerate: { directory: 'design' } }] },
				{ label: 'The decisions', items: [{ autogenerate: { directory: 'adr' } }] },
			],
			plugins: [starlightLinksValidator()],
		}),
	],
});
