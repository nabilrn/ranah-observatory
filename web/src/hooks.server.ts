import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  const lang = event.params.lang === 'en' ? 'en' : 'id';
  return resolve(event, {
    transformPageChunk: ({ html }) => html.replace('__LANG__', lang)
  });
};
