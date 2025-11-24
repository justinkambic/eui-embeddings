import type { AppProps } from "next/app";
import { EuiProvider } from "@elastic/eui";
import { useEffect } from "react";
import { initRum } from "../lib/rum";

export default function App({ Component, pageProps }: AppProps) {
  // Initialize RUM agent on client-side only
  useEffect(() => {
    if (typeof window !== 'undefined') {
      initRum();
    }
  }, []);

  return (
    <EuiProvider colorMode="light">
      <Component {...pageProps} />
    </EuiProvider>
  );
}

