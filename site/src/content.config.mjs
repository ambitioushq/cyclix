import { defineCollection } from 'astro:content';
import { docsSchema } from '@astrojs/starlight/schema';
import { docsFolderLoader } from './docs.mjs';

export const collections = {
	docs: defineCollection({ loader: docsFolderLoader(), schema: docsSchema() }),
};
