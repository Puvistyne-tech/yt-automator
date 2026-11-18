const MAX_ACRONYM_LENGTH = 3;

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function isAcronym(word: string): boolean {
  return /^[a-z]+$/i.test(word) && (word.length <= MAX_ACRONYM_LENGTH || !/[aeiou]/i.test(word));
}

export function humanizeId(id: string): string {
  const spaced = id.replace(/[_-]+/g, " ").trim();
  if (isAcronym(spaced)) {
    return spaced.toUpperCase();
  }
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
