const pairs: Record<string, string> = {
  a:'а', b:'б', v:'в', g:'г', d:'д', đ:'ђ', e:'е', ž:'ж', z:'з', i:'и', j:'ј',
  k:'к', l:'л', m:'м', n:'н', o:'о', p:'п', r:'р', s:'с', t:'т', ć:'ћ', u:'у',
  f:'ф', h:'х', c:'ц', č:'ч', š:'ш', lj:'љ', nj:'њ', dž:'џ',
}

// Only UI copy is transliterated. Published product names and brands are data.
export function transliterate(text: string): string {
  return text.replace(/dž|lj|nj|[a-zđžćčš]/gi, (part) => {
    const value = pairs[part.toLowerCase()] ?? part
    return part[0] === part[0].toUpperCase() ? value.toUpperCase() : value
  })
}
