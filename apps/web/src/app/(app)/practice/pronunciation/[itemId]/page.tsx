"use client";

import { use, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { findItem, getUploadUrl, postAttempt, scoreSpeech, uploadAudio } from "@/lib/api/endpoints";
import { AudioButton } from "@/components/AudioButton";
import { Card, ErrorNote, Kicker, LoadingNote, PageTitle, VoiceCredit } from "@/components/ui";
import type { PronReport } from "@/lib/api/types";

function scoreWord(overall: number): string {
  if (overall >= 85) return "Clear";
  if (overall >= 70) return "Close";
  if (overall >= 50) return "Getting there";
  return "Keep going";
}

export default function PronunciationPage({
  params,
}: {
  params: Promise<{ itemId: string }>;
}) {
  const { itemId } = use(params);
  const itemQuery = useQuery({ queryKey: ["item", itemId], queryFn: () => findItem(itemId) });

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

  if (itemQuery.isPending) return <LoadingNote label="Fetching the phrase…" />;
  if (itemQuery.isError || !itemQuery.data) {
    return <ErrorNote message="That phrase couldn't be found. Head back and pick another." />;
  }

  const item = itemQuery.data;

  return (
    <div className="grid gap-6">
      <div>
        <Kicker>Practice · Pronunciation</Kicker>
        <PageTitle>Say it like Kigali says it.</PageTitle>
      </div>

      <Card testid="target-phrase">
        <Kicker>Target phrase</Kicker>
        <p className="ky mt-3 text-3xl leading-snug sm:text-4xl">{item.sentence}</p>
        <p className="mt-1 text-ink-soft">{item.gloss}</p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-line bg-paper py-1 pr-4 pl-1">
            <AudioButton itemId={item.id} testid="play-native" />
            <span className="text-[10px] font-semibold tracking-[0.16em] text-ink-soft uppercase">
              Diane · Native
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-line bg-paper py-1 pr-4 pl-1">
            <AudioButton itemId={item.id} slow testid="play-slow" />
            <span className="text-[10px] font-semibold tracking-[0.16em] text-ink-soft uppercase">
              Listen slowed down
            </span>
          </div>
        </div>
      </Card>

      <Card testid="recording-card">
        {error ? <ErrorNote message={error} testid="pron-error" /> : null}
        <div className="mt-1 flex flex-col items-center gap-4 py-4">
          {report ? (
            <div className="text-center" data-testid="pron-score">
              <p className="ky text-6xl font-semibold text-accent-deep">
                {Math.round(report.overall)}
              </p>
              <p className="text-[11px] font-semibold tracking-[0.2em] text-ink-soft uppercase">
                {scoreWord(report.overall)} · You · Take {take}
              </p>
            </div>
          ) : (
            <p className="text-sm text-ink-soft">
              Listen once, then record. Tone marks matter — flat tone is the #1 foreign tell.
            </p>
          )}
          <button
            type="button"
            onClick={toggleRecord}
            disabled={scoring}
            data-testid="record-button"
            aria-pressed={recording}
            className={`rounded-full px-7 py-3.5 font-medium transition-colors disabled:opacity-60 ${
              recording
                ? "bg-ink text-paper"
                : "bg-accent text-paper hover:bg-accent-deep"
            }`}
          >
            {scoring
              ? "Listening back…"
              : recording
                ? "■ Stop"
                : `● Record take ${take + 1}`}
          </button>
        </div>

        {report ? (
          <div className="mt-2 border-t border-line pt-5">
            <h2 className="ky text-lg font-semibold">What to fix</h2>
            <ul className="mt-3 grid gap-2" data-testid="phoneme-chips">
              {report.phonemes.map((p, i) => (
                <li
                  key={`${p.phoneme}-${i}`}
                  data-testid="phoneme-chip"
                  className="flex items-start gap-3 rounded-xl border border-line bg-paper px-4 py-3"
                >
                  <span className="ky rounded-lg bg-cream px-2.5 py-1 text-lg leading-none">
                    {p.phoneme}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
                      {Math.round(p.score)} / 100
                    </p>
                    {p.note ? <p className="mt-0.5 text-sm leading-relaxed">{p.note}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
            {report.tone_flags.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2" data-testid="tone-flags">
                {report.tone_flags.map((flag) => (
                  <span
                    key={flag}
                    data-testid="tone-flag"
                    className="rounded-full border border-accent/30 bg-accent-soft px-3 py-1 text-xs text-accent-deep"
                  >
                    ♪ {flag}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </Card>

      <div className="flex justify-center">
        <VoiceCredit name="Diane" />
      </div>
    </div>
  );
}
