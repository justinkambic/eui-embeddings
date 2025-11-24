/**
 * Next.js Instrumentation Hook
 * 
 * This file is automatically executed by Next.js when the server starts.
 * It initializes OpenTelemetry SDK for server-side instrumentation.
 * 
 * See: https://nextjs.org/docs/advanced-features/instrumentation
 */

export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    // Only run on Node.js runtime (server-side)
    const { NodeSDK } = await import('@opentelemetry/sdk-node');
    const { HttpInstrumentation } = await import('@opentelemetry/instrumentation-http');
    const { FetchInstrumentation } = await import('@opentelemetry/instrumentation-fetch');
    const { OTLPTraceExporter } = await import('@opentelemetry/exporter-trace-otlp-http');
    const { OTLPMetricExporter } = await import('@opentelemetry/exporter-metrics-otlp-http');
    const { Resource } = await import('@opentelemetry/resources');
    const { SEMRESATTRS_SERVICE_NAME, SEMRESATTRS_SERVICE_VERSION } = await import('@opentelemetry/semantic-conventions');
    const { PeriodicExportingMetricReader } = await import('@opentelemetry/sdk-metrics');

    // Configuration from environment variables
    const serviceName = process.env.NEXT_PUBLIC_OTEL_SERVICE_NAME || process.env.OTEL_SERVICE_NAME || 'eui-frontend';
    const serviceVersion = process.env.NEXT_PUBLIC_OTEL_SERVICE_VERSION || process.env.OTEL_SERVICE_VERSION || 'unknown';
    const otlpEndpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 
      'https://ff29e674b8bb4b06b3e71aaacf84879f.ingest.us-central1.gcp.elastic.cloud:443';
    const otlpHeaders = process.env.OTEL_EXPORTER_OTLP_HEADERS || 
      'Authorization=ApiKey ZjlhVnRwb0JITGJzUkpwVXhNR0w6S1htMDVsWHJPbW1yczFMOEo0QTFxdw==';
    const deploymentEnvironment = process.env.NEXT_PUBLIC_DEPLOYMENT_ENVIRONMENT || 
      process.env.OTEL_RESOURCE_ATTRIBUTES?.split(',').find(attr => attr.startsWith('deployment.environment='))?.split('=')[1] ||
      'production';

    // Parse headers
    const headers: Record<string, string> = {};
    otlpHeaders.split(',').forEach(header => {
      const [key, ...valueParts] = header.split('=');
      if (key && valueParts.length > 0) {
        headers[key.trim()] = valueParts.join('=').trim();
      }
    });

    // Create resource attributes
    const resourceAttributes: Record<string, string> = {
      [SEMRESATTRS_SERVICE_NAME]: serviceName,
      [SEMRESATTRS_SERVICE_VERSION]: serviceVersion,
      'deployment.environment': deploymentEnvironment,
    };

    // Initialize OpenTelemetry SDK
    // Note: Using type assertion to work around TypeScript version compatibility issue
    // between @opentelemetry/sdk-node and @opentelemetry/sdk-metrics
    const metricReader = new PeriodicExportingMetricReader({
      exporter: new OTLPMetricExporter({
        url: `${otlpEndpoint}/v1/metrics`,
        headers,
      }),
      exportIntervalMillis: 60000, // Export every 60 seconds
    });

    const sdk = new NodeSDK({
      resource: new Resource(resourceAttributes),
      traceExporter: new OTLPTraceExporter({
        url: `${otlpEndpoint}/v1/traces`,
        headers,
      }),
      metricReader: metricReader as any, // Type assertion to resolve version compatibility
      instrumentations: [
        new HttpInstrumentation(),
        new FetchInstrumentation(),
      ],
    });

    // Start the SDK
    sdk.start();
    console.log(`[OTEL] OpenTelemetry initialized for service: ${serviceName} (version: ${serviceVersion})`);
    console.log(`[OTEL] OTLP endpoint: ${otlpEndpoint}`);

    // Graceful shutdown
    process.on('SIGTERM', () => {
      sdk.shutdown()
        .then(() => console.log('[OTEL] OpenTelemetry terminated'))
        .catch((error) => console.error('[OTEL] Error terminating OpenTelemetry', error))
        .finally(() => process.exit(0));
    });
  }
}

