package com.hdmechanic.crm;

import android.annotation.SuppressLint;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.SslErrorHandler;
import android.net.http.SslError;
import android.graphics.Bitmap;
import android.widget.ProgressBar;
import androidx.appcompat.app.AppCompatActivity;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private ProgressBar progressBar;
    private static final String BASE_URL = "https://hdmechaniccrm.onrender.com";
    private static final String TAG = "HDMechanic";

    private final ExecutorService analyticsExecutor = Executors.newSingleThreadExecutor();
    private String sessionId;
    private long pageLoadStartTime;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        sessionId = UUID.randomUUID().toString();
        installCrashHandler();

        webView = findViewById(R.id.webview);
        progressBar = findViewById(R.id.progressbar);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                progressBar.setVisibility(View.VISIBLE);
                pageLoadStartTime = System.currentTimeMillis();
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                long loadTime = System.currentTimeMillis() - pageLoadStartTime;
                reportPageView(url, loadTime);
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.proceed();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
            }
        });

        webView.loadUrl(BASE_URL);
        createSession();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    protected void onRestoreInstanceState(Bundle savedInstanceState) {
        super.onRestoreInstanceState(savedInstanceState);
        webView.restoreState(savedInstanceState);
    }

    private void installCrashHandler() {
        final Thread.UncaughtExceptionHandler defaultHandler = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            @Override
            public void uncaughtException(Thread t, Throwable e) {
                try {
                    String deviceInfo = Build.MANUFACTURER + " " + Build.MODEL
                            + " (Android " + Build.VERSION.RELEASE + ", API " + Build.VERSION.SDK_INT + ")";
                    String errorType = e.getClass().getSimpleName();
                    String errorMessage = e.getMessage() != null ? e.getMessage() : "Unknown";
                    String stackTrace = Log.getStackTraceString(e);

                    String json = "{\"platform\":\"android\""
                            + ",\"app_version\":\"1.0.0\""
                            + ",\"error_type\":\"" + escapeJson(errorType) + "\""
                            + ",\"error_message\":\"" + escapeJson(errorMessage) + "\""
                            + ",\"stack_trace\":\"" + escapeJson(stackTrace) + "\""
                            + ",\"device_info\":\"" + escapeJson(deviceInfo) + "\""
                            + "}";

                    postToAnalytics("/api/analytics/crash", json);
                } catch (Exception ignored) {
                }

                if (defaultHandler != null) {
                    defaultHandler.uncaughtException(t, e);
                } else {
                    System.exit(1);
                }
            }
        });
    }

    private void createSession() {
        String deviceInfo = Build.MANUFACTURER + " " + Build.MODEL
                + " (Android " + Build.VERSION.RELEASE + ", API " + Build.VERSION.SDK_INT + ")";

        String json = "{\"platform\":\"android\""
                + ",\"app_version\":\"1.0.0\""
                + ",\"device_info\":\"" + escapeJson(deviceInfo) + "\""
                + "}";

        analyticsExecutor.execute(new Runnable() {
            @Override
            public void run() {
                try {
                    String result = postToAnalytics("/api/analytics/session", json);
                    if (result != null && result.contains("\"session_id\"")) {
                        String id = result.replaceAll(".*\"session_id\"\\s*:\\s*", "").replaceAll("[^0-9].*", "");
                        if (!id.isEmpty()) {
                            sessionId = id;
                        }
                    }
                } catch (Exception e) {
                    Log.d(TAG, "Analytics session create failed: " + e.getMessage());
                }
            }
        });
    }

    private void reportPageView(final String url, long loadTimeMs) {
        String path = url.replaceFirst("^https?://[^/]+", "");
        if (path.isEmpty()) path = "/";

        String json = "{\"platform\":\"android\""
                + ",\"path\":\"" + escapeJson(path) + "\""
                + ",\"load_time_ms\":" + loadTimeMs
                + ",\"session_id\":\"" + sessionId + "\""
                + "}";

        analyticsExecutor.execute(new Runnable() {
            @Override
            public void run() {
                try {
                    postToAnalytics("/api/analytics/pageview", json);
                } catch (Exception e) {
                    Log.d(TAG, "Analytics pageview failed: " + e.getMessage());
                }
            }
        });
    }

    private String postToAnalytics(String endpoint, String jsonBody) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(BASE_URL + endpoint);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);

            OutputStream os = conn.getOutputStream();
            os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
            os.flush();
            os.close();

            int code = conn.getResponseCode();
            if (code >= 200 && code < 300) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
                reader.close();
                return sb.toString();
            }
        } catch (Exception e) {
            Log.d(TAG, "Analytics POST failed for " + endpoint + ": " + e.getMessage());
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
        return null;
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
