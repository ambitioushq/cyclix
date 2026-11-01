import { readFileSync } from 'node:fs';
import { posix, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { glob } from 'astro/loaders';
import { markdownToMdast } from 'satteri';

/** The docs folder at the top of the repository: the only copy of the pages. */
export const docsDir = fileURLToPath(new URL('../../docs/', import.meta.url));

const repository = 'https://github.com/ambitioushq/cyclix/blob/main/';

/** Markdown files under docs/ that are not pages on the site. */
const notPages = ['adr/TEMPLATE.md'];

function isPage(file) {
	return file.endsWith('.md') && !file.startsWith('../') && !notPages.includes(file);
}

/** The page id of a Markdown file under docs/: its path without `.md`, with a README as its folder's index. */
function pageId(file) {
	const id = file.replace(/\.md$/, '').replace(/(^|\/)README$/, '');
	return id === '' ? 'index' : id.toLowerCase();
}

function route(id) {
	return id === 'index' ? '/' : `/${id}/`;
}

/** Whether a top-level node is the page's title: its first level-one heading. */
function isTitle(node) {
	return node.type === 'heading' && node.depth === 1;
}

function plainText(node) {
	return node.value ?? (node.children ?? []).map(plainText).join('');
}

/** The page's title, read with the parser that renders the page, so it names the heading the plugin removes. */
function title(text) {
	const heading = markdownToMdast(text).children.find(isTitle);
	return heading && plainText(heading);
}

/**
 * Loads every page under docs/ into the Starlight `docs` collection. Each page takes
 * its title from its first heading, so the files need no frontmatter.
 */
export function docsFolderLoader() {
	const loader = glob({
		base: docsDir,
		pattern: ['**/*.md', ...notPages.map((file) => `!${file}`)],
		generateId: ({ entry }) => pageId(entry),
	});
	return {
		name: 'cyclix-docs-folder-loader',
		load: (context) =>
			loader.load({
				...context,
				parseData: ({ data, filePath, ...rest }) =>
					context.parseData({
						...rest,
						filePath,
						data: { title: title(readFileSync(filePath, 'utf8')), ...data },
					}),
			}),
	};
}

function rewrite(url, from) {
	if (/^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith('#') || url.startsWith('/')) return url;
	const [path, hash] = url.split(/#(.*)/s);
	const target = posix.normalize(posix.join(posix.dirname(from), path));
	const anchor = hash === undefined ? '' : `#${hash}`;
	if (isPage(target)) return route(pageId(target)) + anchor;
	return repository + posix.normalize(posix.join('docs', target)) + anchor;
}

/**
 * A Sätteri plugin that fits a page from docs/ to the site. It removes the first
 * level-one heading, which Starlight shows as the title. It points each relative link
 * at the page it names, or at the file on GitHub when the target is not a page.
 */
export function docsFolderPlugin({ fileURL }) {
	const path = fileURL && fileURLToPath(fileURL);
	if (!path?.startsWith(docsDir)) return null;
	const from = relative(docsDir, path).split(sep).join('/');
	const id = pageId(from);
	return {
		name: 'cyclix-docs-folder',
		before(root, ctx) {
			const heading = root.children.find(isTitle);
			if (heading) ctx.removeNode(heading);
			// The links validator finds a page by its path under src/content/docs, unless the
			// frontmatter names a slug. These pages live outside that folder, so the slug names
			// the page. An empty slug is ignored, so the home page cannot be named this way.
			if (id !== 'index') ctx.data.astro.frontmatter = { ...ctx.data.astro.frontmatter, slug: id };
		},
		link: (node, ctx) => ctx.setProperty(node, 'url', rewrite(node.url, from)),
		definition: (node, ctx) => ctx.setProperty(node, 'url', rewrite(node.url, from)),
	};
}
