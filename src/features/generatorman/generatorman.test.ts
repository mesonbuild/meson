import { describe, expect, it } from 'vitest'
import { creategeneratorman } from './generatorman'

describe('creategeneratorman', () => {
  it('keeps its contract stable', () => {
    expect(creategeneratorman({ id: 'demo' })).toEqual({ id: 'demo' })
  })
})
