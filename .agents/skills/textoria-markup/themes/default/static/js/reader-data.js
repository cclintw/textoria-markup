/* Adapter only: keep Textoria's existing data and the reference reader independent. */
const READER_DATA = window.TEXTORIA_WORKBENCH;
const READER_PAGE = JSON.parse(document.getElementById('annotationPage').textContent);
const READER_TYPES = new Map(READER_DATA.types.map(t => [t.markup_id,t]));
const AUTHORITY = READER_DATA.terms.map(t => ({
  ...t, authority_id:t.term_id, entity_text:t.canonical_name, entity_type:t.markup_id,
  source:'Textoria', count:t.occurrences || 0,
}));
