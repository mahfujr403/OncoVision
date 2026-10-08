import test from 'node:test';
import assert from 'node:assert/strict';
import { parseSSEStream } from './sseParser.ts';
import type { ParsedSSEEvent } from './sseParser.ts';

function createMockStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

test('SSE Parser: parses standard single event', async () => {
  const chunks = ['event: status\ndata: {"stage":"starting","message":"Starting"}\n\n'];
  const events: ParsedSSEEvent[] = [];

  await parseSSEStream(createMockStream(chunks), (ev) => events.push(ev));

  assert.equal(events.length, 1);
  assert.equal(events[0].event, 'status');
  assert.deepEqual(JSON.parse(events[0].data), { stage: 'starting', message: 'Starting' });
});

test('SSE Parser: handles fragmented SSE chunks across arbitrary byte boundaries', async () => {
  const chunks = [
    'event: sta',
    'tus\ndata: {"stage":',
    '"retrieving"}\n',
    '\nevent: sources\nda',
    'ta: {"sources":[{"source_id":"S1"}]}\n\n',
  ];
  const events: ParsedSSEEvent[] = [];

  await parseSSEStream(createMockStream(chunks), (ev) => events.push(ev));

  assert.equal(events.length, 2);
  assert.equal(events[0].event, 'status');
  assert.equal(JSON.parse(events[0].data).stage, 'retrieving');
  assert.equal(events[1].event, 'sources');
  assert.equal(JSON.parse(events[1].data).sources[0].source_id, 'S1');
});

test('SSE Parser: handles status, sources, delta accumulation, and done event sequence', async () => {
  const ssePayload = [
    'event: status\ndata: {"stage":"retrieving","message":"Querying"}\n\n',
    'event: sources\ndata: {"sources":[{"source_id":"S1","title":"WHO Guidelines"}]}\n\n',
    'event: status\ndata: {"stage":"synthesizing","message":"Generating"}\n\n',
    'event: delta\ndata: {"text":"Lung adenocarcinoma "}\n\n',
    'event: delta\ndata: {"text":"exhibits glandular structures [S1]."}\n\n',
    'event: done\ndata: {"grounded":true,"citations":[],"conversation_id":"c-123"}\n\n',
  ];

  const events: ParsedSSEEvent[] = [];
  let accumulatedText = '';

  await parseSSEStream(createMockStream(ssePayload), (ev) => {
    events.push(ev);
    if (ev.event === 'delta') {
      const parsed = JSON.parse(ev.data);
      accumulatedText += parsed.text;
    }
  });

  assert.equal(events.length, 6);
  assert.equal(events[0].event, 'status');
  assert.equal(events[1].event, 'sources');
  assert.equal(events[2].event, 'status');
  assert.equal(events[3].event, 'delta');
  assert.equal(events[4].event, 'delta');
  assert.equal(events[5].event, 'done');

  assert.equal(accumulatedText, 'Lung adenocarcinoma exhibits glandular structures [S1].');

  const doneEvent = JSON.parse(events[5].data);
  assert.equal(doneEvent.grounded, true);
  assert.equal(doneEvent.conversation_id, 'c-123');
});

test('SSE Parser: handles controlled error events', async () => {
  const chunks = ['event: error\ndata: {"error_type":"generation_timeout","message":"Timeout"}\n\n'];
  const events: ParsedSSEEvent[] = [];

  await parseSSEStream(createMockStream(chunks), (ev) => events.push(ev));

  assert.equal(events.length, 1);
  assert.equal(events[0].event, 'error');
  const err = JSON.parse(events[0].data);
  assert.equal(err.error_type, 'generation_timeout');
});

test('SSE Parser: supports AbortController cancellation', async () => {
  const abortController = new AbortController();
  const encoder = new TextEncoder();

  const infiniteStream = new ReadableStream<Uint8Array>({
    pull(controller) {
      controller.enqueue(encoder.encode('event: delta\ndata: {"text":"chunk"}\n\n'));
    },
  });

  const events: ParsedSSEEvent[] = [];
  const streamPromise = parseSSEStream(
    infiniteStream,
    (ev) => {
      events.push(ev);
      // Abort after first chunk received
      abortController.abort();
    },
    abortController.signal,
  );

  await streamPromise;
  assert.ok(events.length >= 1);
  assert.ok(abortController.signal.aborted);
});
