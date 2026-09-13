import { useEffect, useId, useState } from 'react'

import { searchCityAddresses } from '../../services/cities'
import type { AddressMatch, AddressSearchResult } from '../../types/city'

interface AddressAutocompleteProps {
  cityId: string
  onSelect?: (address: AddressMatch) => void
}

export function AddressAutocomplete({ cityId, onSelect }: AddressAutocompleteProps) {
  const listId = useId()
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<AddressSearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 3) {
      setResult(null)
      setError(null)
      setLoading(false)
      return
    }

    let active = true
    const timer = window.setTimeout(() => {
      setLoading(true)
      setError(null)
      void searchCityAddresses(cityId, trimmed)
        .then((response) => {
          if (active) setResult(response)
        })
        .catch((requestError: unknown) => {
          if (!active) return
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Não foi possível pesquisar o endereço.',
          )
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }, 250)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [cityId, query])

  function choose(address: AddressMatch) {
    setQuery(address.formatted)
    setResult(null)
    onSelect?.(address)
  }

  return (
    <div className="address-search">
      <label htmlFor={`${listId}-input`}>Explorar endereço válido</label>
      <div className="address-search-input-wrap">
        <input
          id={`${listId}-input`}
          role="combobox"
          aria-autocomplete="list"
          aria-controls={listId}
          aria-expanded={Boolean(result?.matches.length)}
          autoComplete="off"
          placeholder="Ex.: Rua das Acácias, 593"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {loading ? <span className="address-search-spinner">Buscando…</span> : null}
      </div>

      {result && (result.matches.length > 0 || result.number_suggestions.length > 0) ? (
        <div className="address-search-results" id={listId} role="listbox">
          {result.street_suggestion ? (
            <p className="address-search-hint">
              Logradouro sugerido: <strong>{result.street_suggestion}</strong>
            </p>
          ) : null}
          {result.matches.map((address) => (
            <button
              key={address.id}
              type="button"
              role="option"
              aria-selected="false"
              onClick={() => choose(address)}
            >
              <strong>{address.street_name}, {address.house_number}</strong>
              <span>{address.district_name}</span>
            </button>
          ))}
          {result.matches.length === 0 && result.number_suggestions.length > 0 ? (
            <p className="address-search-hint">
              Número não encontrado. Próximos existentes:{' '}
              <strong>{result.number_suggestions.join(', ')}</strong>
            </p>
          ) : null}
        </div>
      ) : null}

      {result && result.matches.length === 0 && result.number_suggestions.length === 0 ? (
        <p className="address-search-empty">Nenhum endereço existente corresponde à busca.</p>
      ) : null}
      {error ? <p className="address-search-error">{error}</p> : null}
    </div>
  )
}
