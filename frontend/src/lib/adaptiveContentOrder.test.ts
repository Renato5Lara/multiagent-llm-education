// Ejecutar: node --experimental-strip-types --test src/lib/adaptiveContentOrder.test.ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { availableContentOrder } from './adaptiveContentOrder.ts'

const blocksOf = (...types: string[]) => types.map(type => ({ type }))

const DECISION_ORDER = ['theory', 'example', 'diagram', 'video', 'exercise', 'simulation', 'game']

test('A: los tipos que el tema no tiene (diagram/video) no se anuncian y el orden se conserva', () => {
  const blocks = blocksOf('theory', 'example', 'exercise', 'game', 'simulation')

  assert.deepEqual(
    availableContentOrder(DECISION_ORDER, blocks),
    ['theory', 'example', 'exercise', 'simulation', 'game'],
  )
})

test('A: la lista resultante no tiene huecos (la numeración 1..n es consecutiva)', () => {
  const announced = availableContentOrder(DECISION_ORDER, blocksOf('theory', 'example', 'exercise', 'simulation', 'game'))

  assert.deepEqual(announced.map((_, idx) => idx + 1), [1, 2, 3, 4, 5])
})

test('B: si todos los tipos existen se devuelven todos, en el orden exacto de contentOrder', () => {
  const blocks = blocksOf(...[...DECISION_ORDER].reverse())

  assert.deepEqual(availableContentOrder(DECISION_ORDER, blocks), DECISION_ORDER)
})

test('C: sin bloques devuelve []', () => {
  assert.deepEqual(availableContentOrder(DECISION_ORDER, []), [])
})

test('C: con bloques de tipos no reconocidos devuelve []', () => {
  assert.deepEqual(availableContentOrder(DECISION_ORDER, blocksOf('foo', 'bar')), [])
})
