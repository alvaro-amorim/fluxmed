import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AddressAutocomplete } from './AddressAutocomplete'

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AddressAutocomplete', () => {
  it('lists only addresses returned by the backend and selects one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        response({
          query: 'Rua das Acacias',
          street_suggestion: 'Rua das Acácias',
          number_suggestions: [],
          matches: [
            {
              id: 'address-1',
              street_name: 'Rua das Acácias',
              house_number: '593',
              district_name: 'Jardim das Flores',
              complement: null,
              formatted: 'Rua das Acácias, 593 — Jardim das Flores',
              longitude: -46.62,
              latitude: -22.4,
            },
          ],
        }),
      ),
    )
    const onSelect = vi.fn()
    render(<AddressAutocomplete cityId="city-1" onSelect={onSelect} />)
    const user = userEvent.setup()

    await user.type(screen.getByRole('combobox'), 'Rua das Acacias')

    const option = await screen.findByRole('option')
    expect(screen.getByText('Logradouro sugerido:', { exact: false })).toBeInTheDocument()
    await user.click(option)

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'address-1' }))
    expect(screen.getByRole('combobox')).toHaveValue(
      'Rua das Acácias, 593 — Jardim das Flores',
    )
  })

  it('shows nearest existing numbers without silently accepting one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        response({
          query: 'Rua das Acácias, 600',
          street_suggestion: null,
          number_suggestions: ['593', '611'],
          matches: [],
        }),
      ),
    )
    render(<AddressAutocomplete cityId="city-1" />)
    const user = userEvent.setup()

    await user.type(screen.getByRole('combobox'), 'Rua das Acácias, 600')

    expect(await screen.findByText(/Número não encontrado/)).toHaveTextContent('593, 611')
    expect(screen.queryByRole('option')).not.toBeInTheDocument()
  })
})
