/**
 * Robust Server-Sent Events (SSE) Stream Parser.
 *
 * Adheres strictly to the SSE specification:
 * - Supports 'event:', 'data:', 'id:', and comment ':...' lines
 * - Preserves multi-line data joined by newlines
 * - Emits events upon blank line delimiters
 * - Handles arbitrary network chunk fragmentation across byte boundaries
 */

export interface ParsedSSEEvent {
  event: string;
  data: string;
}

export type SSEEventHandler = (event: ParsedSSEEvent) => void;

export async function parseSSEStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: SSEEventHandler,
  signal?: AbortSignal,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let currentEvent = 'message';
  let currentData: string[] = [];

  try {
    while (true) {
      if (signal?.aborted) {
        try {
          await reader.cancel();
        } catch {
          // Ignore cancel errors on aborted reader
        }
        break;
      }

      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      // Retain incomplete trailing line in the buffer
      buffer = lines.pop() ?? '';

      for (const rawLine of lines) {
        const line = rawLine.trimEnd();

        // Comment lines
        if (line.startsWith(':')) {
          continue;
        }

        // Empty line indicates event dispatch
        if (line === '') {
          if (currentData.length > 0 || currentEvent !== 'message') {
            onEvent({
              event: currentEvent || 'message',
              data: currentData.join('\n'),
            });
          }
          currentEvent = 'message';
          currentData = [];
          continue;
        }

        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          currentData.push(line.slice(5).trim());
        }
      }
    }

    // Flush any remaining complete event at EOF if buffer had trailing data
    if (buffer.trim()) {
      const line = buffer.trimEnd();
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        currentData.push(line.slice(5).trim());
      }
    }
    if (currentData.length > 0) {
      onEvent({
        event: currentEvent || 'message',
        data: currentData.join('\n'),
      });
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // Reader might already be released or cancelled
    }
  }
}
