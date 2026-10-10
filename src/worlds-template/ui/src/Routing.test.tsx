import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { getPace, lastRun, setPace, startAgent, stopAgent } from "./harness";
import { AgentCursor } from "./shared/controls/AgentCursor";
import { Narrator } from "./shared/controls/Narrator";

const fetchMock = vi.fn();

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
  window.history.replaceState({}, "", "/");
});

test("agent control uses relative world routes without a build-time port", async () => {
  window.history.replaceState({}, "", "/api/play/world-1/");
  fetchMock.mockReset().mockResolvedValue({ ok: true, json: async () => ({ last: null }) });
  vi.stubGlobal("fetch", fetchMock);
  await startAgent("gemini-flash");
  await stopAgent();
  await lastRun();
  await setPace(0.4);
  await getPace();
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["harness/run", "harness/stop", "harness/status", "harness/pace", "harness/status"]);
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ agent: "gemini-flash" });
});

test("offline takeover unlocks the same world", async () => {
  fetchMock.mockReset().mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: "offline" }) }).mockResolvedValueOnce({ ok: true });
  vi.stubGlobal("fetch", fetchMock);
  expect((await stopAgent()).ok).toBe(true);
  expect(fetchMock.mock.calls[1][0]).toBe("api/action");
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ id: "mode", args: { mode: "you" } });
});

test("narrator fetches text and audio within the world prefix", async () => {
  window.history.replaceState({}, "", "/api/play/world-1/?level=2");
  fetchMock.mockReset().mockResolvedValue({ ok: true, json: async () => ({ text: "Welcome.", sentences: ["Welcome."], audio_url: "/api/narration/intro/audio" }) });
  vi.stubGlobal("fetch", fetchMock);
  const audio = { addEventListener: vi.fn(), play: vi.fn().mockResolvedValue(undefined), pause: vi.fn(), currentTime: 0 };
  const AudioMock = vi.fn(function (url: string) { void url; return audio; });
  vi.stubGlobal("Audio", AudioMock);
  render(<Narrator />);
  await waitFor(() => expect(AudioMock).toHaveBeenCalled());
  expect(fetchMock.mock.calls[0][0]).toBe("api/narration");
  expect(AudioMock.mock.calls[0][0]).toBe(`${window.location.origin}/api/play/world-1/api/narration/intro/audio`);
});

test("cursor uses prefixed events and falls back to incremental polling", async () => {
  vi.useFakeTimers();
  window.history.replaceState({}, "", "/api/play/world-1/");
  fetchMock.mockReset().mockResolvedValue({ ok: true, json: async () => [{ seq: 12, source: "ui" }] });
  vi.stubGlobal("fetch", fetchMock);
  const sockets: { onclose?: () => void; close: () => void }[] = [];
  const SocketMock = vi.fn(function (url: string | URL) {
    void url;
    const socket = { close: vi.fn(), onclose: undefined };
    sockets.push(socket);
    return socket;
  });
  vi.stubGlobal("WebSocket", SocketMock);
  render(<AgentCursor active look={{ label: "Agent", color: "blue" }} />);
  await act(async () => {});
  expect(String(SocketMock.mock.calls[0][0])).toBe(`${window.location.origin.replace(/^http/, "ws")}/api/play/world-1/api/events`);
  act(() => sockets[0].onclose?.());
  await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
  expect(fetchMock.mock.calls.some(([url]) => url === "api/events?after=12")).toBe(true);
});


test("progress commentary and audio stay within the world prefix", async () => {
  vi.useFakeTimers();
  window.history.replaceState({}, "", "/api/play/world-1/");
  fetchMock.mockReset().mockResolvedValueOnce({ ok: true, json: async () => ({ text: "Hello.", sentences: ["Hello."], audio_url: null }) }).mockResolvedValueOnce({ ok: true, json: async () => ({ text: "Making progress.", sentences: ["Making progress."], audio_url: "/api/narration/commentary/audio" }) });
  vi.stubGlobal("fetch", fetchMock);
  const audio = { addEventListener: vi.fn(), play: vi.fn().mockResolvedValue(undefined), pause: vi.fn() };
  const AudioMock = vi.fn(function (url: string) { void url; return audio; });
  vi.stubGlobal("Audio", AudioMock);
  render(<Narrator collapse week={1} />);
  await act(async () => {});
  await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
  fireEvent.click(screen.getByText("How am I doing?"));
  await act(async () => {});
  const call = fetchMock.mock.calls.find(([, options]) => options?.body?.includes("commentary"));
  expect(call?.[0]).toBe("api/narration");
  expect(AudioMock.mock.calls[0][0]).toBe(`${window.location.origin}/api/play/world-1/api/narration/commentary/audio`);
});
