"use client";

import { use, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getRoadmap,
  getUploadUrl,
  itemFromRoadmap,
  postAttempt,
  scoreSpeech,
  uploadAudio,
} from "@/lib/api/endpoints";
import { AudioButton } from "@/components/AudioButton";
import { SaveToNotebook } from "@/components/SaveToNotebook";
import { Card, CardLabel, ErrorNote, Kicker, LoadingNote, PageTitle } from "@/components/ui";
import type { PronReport } from "@/lib/api/types";

// Decorative waveforms, straight from the mockup.
const NATIVE_BARS = [8, 16, 24, 30, 22, 12, 18, 28, 32, 24, 14, 8, 20, 26, 18, 10];
const USER_BARS = [7, 14, 22, 26, 20, 10, 15, 24, 27, 20, 12, 7, 17, 22, 15, 8];

function scoreWord(overall: number): string {
  if (overall >= 85) return "Clear";
  if (overall >= 70) return "Close";
  if (overall >= 50) return "Getting there";
  return "Keep going";
}

function Waveform({ bars, color }: { bars: number[]; color: string }) {
  return (
    <div className="flex h-[34px] flex-1 items-end gap-[2px]" aria-hidden>
      {bars.map((h, i) => (
        <span key={i} className={`w-1 rounded-[2px] ${color}`} style={{ height: `${h}px` }} />
      ))}
    </div>
  );
}

export default function PronunciationPage({
  params,
}: {
  params: Promise<{ itemId: string }>;
}) {
  const { itemId } = use(params);
  // The item lives in the roadmap payload — share the ["roadmap"] cache
  // rather than fetching the heavy roadmap once more for one sentence.
  const roadmapQuery = useQuery({ queryKey: ["roadmap"], queryFn: getRoadmap });
  const item = roadmapQuery.data ? itemFromRoadmap(roadmapQuery.data, itemId) : null;

  const [recording, setRecording] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [take, setTake] = useState(0);
  const [report, setReport] = useState<PronReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const scoreBlob = async (blob: Blob) => {
    setScoring(true);
    setError(null);
    try {
      const { upload_url, audio_ref } = await getUploadUrl({
        content_type: blob.type || "audio/webm",
      });
      await uploadAudio(upload_url, blob);
      const pron = await scoreSpeech({ item_id: itemId, audio_ref });
      setReport(pron);
      setTake((t) => t + 1);
      // Record the speaking attempt so progress and can-do confirmations move.
      void postAttempt({
        item_id: itemId,
        mode: "speak",
        score: pron.overall / 100,
        audio_ref,
      }).catch(() => {});
    } catch {
      setError("Scoring didn't go through — record the take again.");
    } finally {
      setScoring(false);
    }
  };

  const toggleRecord = async () => {
    if (recording) {
      recorderRef.current?.stop();
      return;
    }
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        void scoreBlob(blob);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("We couldn't reach your microphone. Allow mic access and try again.");
    }
  };

  if (roadmapQuery.isPending) return <LoadingNote label="Fetching the phrase…" />;
  if (roadmapQuery.isError || !item) {
    return <ErrorNote message="That phrase couldn't be found. Head back and pick another." />;
  }

  const overall = report ? Math.round(report.overall) : null;
  const scoreTone = overall !== null && overall >= 70 ? "text-green" : "text-gold-text";
  const scoreRing = overall !== null && overall >= 70 ? "border-green" : "border-gold";

  return (
    <div className="grid gap-3.5">
      <div className="mb-2">
        <Kicker>Practice · Pronunciation</Kicker>
        <PageTitle>Say it like Kigali says it.</PageTitle>
      </div>

      <Card testid="target-phrase">
        <div className="flex items-start justify-between gap-3">
          <CardLabel>Target phrase</CardLabel>
          <SaveToNotebook itemId={item.id} />
        </div>
        <p className="ky mt-3 text-[26px] leading-snug font-semibold sm:text-[30px]">
          {item.sentence}
        </p>
        <p className="mt-1 text-[13px] text-ink-soft">{item.gloss}</p>
        <div className="mt-5 flex flex-wrap items-center gap-x-8 gap-y-3">
          <div className="flex min-w-[220px] flex-1 items-center gap-3">
            <AudioButton itemId={item.id} size="sm" testid="play-native" />
            <Waveform bars={NATIVE_BARS} color="bg-accent" />
            <span className="flex-none font-mono text-[10px] text-ink-soft uppercase">
              Native · Kigali
            </span>
          </div>
          <div className="flex items-center gap-3">
            <AudioButton itemId={item.id} slow size="sm" testid="play-slow" />
            <span className="font-mono text-[10px] text-ink-soft uppercase">Slowed down</span>
          </div>
        </div>
      </Card>

      <Card testid="recording-card">
        {error ? <ErrorNote message={error} testid="pron-error" /> : null}
        <div className="flex flex-col items-center gap-6 py-2 sm:flex-row sm:items-center sm:gap-8">
          <div className="flex flex-1 flex-col gap-4">
            {report ? (
              <div className="flex items-center gap-3">
                <Waveform
                  bars={USER_BARS}
                  color={overall !== null && overall >= 70 ? "bg-bark-dot" : "bg-gold"}
                />
                <span className="flex-none font-mono text-[10px] text-ink-soft uppercase">
                  You · Take {take}
                </span>
              </div>
            ) : (
              <p className="text-sm text-ink-soft">
                Listen once, then record. Tone marks matter — flat tone is the #1 foreign tell.
              </p>
            )}
            <div>
              <button
                type="button"
                onClick={toggleRecord}
                disabled={scoring}
                data-testid="record-button"
                aria-pressed={recording}
                className={`cursor-pointer rounded-btn px-5 py-3 text-sm font-semibold transition-colors disabled:cursor-default disabled:opacity-60 ${
                  recording ? "bg-bark text-paper" : "bg-accent text-on-accent hover:bg-accent-hover"
                }`}
              >
                {scoring
                  ? "Listening back…"
                  : recording
                    ? "■ Stop"
                    : `● Record take ${take + 1}`}
              </button>
            </div>
          </div>
          {report && overall !== null ? (
            <div className="flex-none text-center" data-testid="pron-score">
              <p
                className={`ky mx-auto flex h-[74px] w-[74px] items-center justify-center rounded-full border-[3px] text-[26px] font-bold ${scoreRing} ${scoreTone}`}
              >
                {overall}
              </p>
              <p className={`mt-2 text-[11px] font-bold tracking-[0.1em] uppercase ${scoreTone}`}>
                {scoreWord(overall)} · Take {take}
              </p>
            </div>
          ) : null}
        </div>

        {report?.transcript ? (
          <p className="mt-3 text-sm text-ink-soft" data-testid="pron-transcript">
            We heard: <span className="ky font-semibold text-ink">“{report.transcript}”</span>
          </p>
        ) : null}

        {report ? (
          <div className="mt-4 border-t border-line pt-5">
            <CardLabel>What to fix</CardLabel>
            <ul className="mt-3 grid gap-2.5" data-testid="phoneme-chips">
              {report.phonemes.map((p, i) => (
                <li
                  key={`${p.phoneme}-${i}`}
                  data-testid="phoneme-chip"
                  className="flex items-baseline gap-3"
                >
                  <span
                    className={`flex-none rounded-lg px-3 py-1.5 font-mono text-[15px] ${
                      p.score >= 70 ? "bg-green-soft text-green" : "bg-amber-soft text-amber-text"
                    }`}
                  >
                    {p.phoneme}
                  </span>
                  <span className="min-w-0 text-sm leading-[1.55]">
                    <span className="mr-2 font-mono text-[11px] text-ink-faint">
                      {Math.round(p.score)}/100
                    </span>
                    {p.note ?? ""}
                  </span>
                </li>
              ))}
            </ul>
            {report.tone_flags.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2" data-testid="tone-flags">
                {report.tone_flags.map((flag) => (
                  <span
                    key={flag}
                    data-testid="tone-flag"
                    className="rounded-full border border-amber-line bg-amber-soft px-3 py-1 text-xs text-amber-text"
                  >
                    ♪ {flag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </Card>
    </div>
  );
}
