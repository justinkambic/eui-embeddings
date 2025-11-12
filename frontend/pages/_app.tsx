import type { AppProps } from "next/app";
import { EuiProvider } from "@elastic/eui";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <EuiProvider colorMode="light">
      <Component {...pageProps} />
    </EuiProvider>
  );
}

