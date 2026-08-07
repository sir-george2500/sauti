"use client";

import { useEffect, useRef, useState } from "react";
import { ttsUrl } from "@/lib/api/client";

/**
 * Play button for a curriculum item's native audio via GET /tts/{item_id}
 * (302 to the audio file — stub silence in MVP, shape final).
 */
export function AudioButton({
  itemId,
  label,
  slow = false,
  testid = "play-audio",
  className = "",
}: {
  itemId: string;
  label?: string;
  /** Playback at 0.65x for "listen slowed down". */
  slow?: boolean;
  testid?: string;
  className?: string;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  const toggle = () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (!audioRef.current) {
      const audio = new Audio(ttsUrl(itemId));
      audio.addEventListener("ended", () => setPlaying(false));
      audio.addEventListener("error", () => setPlaying(false));
      audioRef.current = audio;
    }
    audioRef.current.playbackRate = slow ? 0.65 : 1;
    void audioRef.current.play().catch(() => setPlaying(false));
    setPlaying(true);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      data-testid={testid}
      aria-label={label ?? (playing ? "Pause audio" : "Play audio")}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line bg-cream text-accent-deep transition-colors hover:border-accent hover:bg-accent-soft ${className}`}
    >
      {playing ? (
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 fill-current" aria-hidden>
          <rect x="3" y="2" width="3.5" height="12" rx="1" />
          <rect x="9.5" y="2" width="3.5" height="12" rx="1" />
        </svg>
      ) : (
        <svg viewBox="0 0 16 16" className="ml-0.5 h-3.5 w-3.5 fill-current" aria-hidden>
          <path d="M4 2.5v11a.6.6 0 0 0 .92.5l8.4-5.5a.6.6 0 0 0 0-1L4.92 2a.6.6 0 0 0-.92.5Z" />
        </svg>
      )}
      {label ? <span className="sr-only">{label}</span> : null}
    </button>
  );
}
