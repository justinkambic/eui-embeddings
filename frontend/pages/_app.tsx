import type { AppProps } from "next/app";
import { EuiProvider } from "@elastic/eui";
import { useEffect, useMemo } from "react";
import { CacheProvider, EmotionCache } from "@emotion/react";
import { createEmotionCache } from "../lib/emotionCache";
import { initRum } from "../lib/rum";

interface MyAppProps extends AppProps {
  emotionCache?: EmotionCache;
}

export default function App({ Component, pageProps, emotionCache }: MyAppProps) {
  // Initialize RUM agent on client-side only
  useEffect(() => {
    if (typeof window !== 'undefined') {
      initRum();
      // Mark body as ready once React has mounted to prevent FOUC
      document.body.classList.add('ready');
    }
  }, []);

  // Use provided cache (from SSR) or create new one (client-side)
  const cache = useMemo(() => {
    if (emotionCache) {
      return emotionCache;
    }
    if (typeof window !== 'undefined') {
      return createEmotionCache();
    }
    return null;
  }, [emotionCache]);

  // If no cache, render without CacheProvider (shouldn't happen in practice)
  if (!cache) {
    return (
      <EuiProvider colorMode="light">
        <Component {...pageProps} />
      </EuiProvider>
    );
  }

  return (
    <CacheProvider value={cache}>
      <EuiProvider colorMode="light">
        <Component {...pageProps} />
      </EuiProvider>
    </CacheProvider>
  );
}

