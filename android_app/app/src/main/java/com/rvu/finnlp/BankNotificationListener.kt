package com.rvu.finnlp

import android.app.Notification
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import androidx.core.content.ContextCompat

class BankNotificationListener : NotificationListenerService() {

    private val scanReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            scanActiveNotifications()
        }
    }

    override fun onCreate() {
        super.onCreate()
        val filter = IntentFilter("com.rvu.finnlp.SCAN_ACTIVE_NOTIFICATIONS")
        ContextCompat.registerReceiver(
            this,
            scanReceiver,
            filter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            unregisterReceiver(scanReceiver)
        } catch (_: Exception) {}
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.d("FinNLP", "BankNotificationListener connected, scanning active notifications")
        scanActiveNotifications()
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        try {
            requestRebind(ComponentName(applicationContext, BankNotificationListener::class.java))
        } catch (_: Exception) {}
    }

    private fun scanActiveNotifications() {
        try {
            val active = activeNotifications ?: return
            for (sbn in active) {
                processStatusBarNotification(sbn)
            }
        } catch (e: Exception) {
            Log.e("FinNLP", "Error scanning active notifications", e)
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        if (sbn != null) {
            processStatusBarNotification(sbn)
        }
    }

    private fun processStatusBarNotification(sbn: StatusBarNotification) {
        val pkg = sbn.packageName ?: return
        if (pkg == packageName) return

        val notif = sbn.notification ?: return
        val extras = notif.extras
        val candidateTexts = mutableListOf<String>()

        if (extras != null) {
            val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
            extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()?.let {
                candidateTexts.add(if (title.isNotBlank() && !it.contains(title)) "$title: $it" else it)
            }
            extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.let {
                candidateTexts.add(if (title.isNotBlank() && !it.contains(title)) "$title: $it" else it)
            }
            extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)?.forEach { line ->
                line?.toString()?.let { candidateTexts.add(it) }
            }
            @Suppress("DEPRECATION")
            val msgBundles = extras.getParcelableArray(Notification.EXTRA_MESSAGES)
            if (msgBundles != null) {
                for (parcelable in msgBundles) {
                    if (parcelable is Bundle) {
                        val msgText = parcelable.getCharSequence("text")?.toString()
                        if (!msgText.isNullOrBlank()) {
                            candidateTexts.add(msgText)
                        }
                    }
                }
            }
        }

        notif.tickerText?.toString()?.let {
            if (it.isNotBlank()) candidateTexts.add(it)
        }

        val appLabel = when {
            pkg.contains("instagram") -> "Instagram"
            pkg.contains("whatsapp") -> "WhatsApp"
            pkg.contains("gm") || pkg.contains("mail") -> "Gmail"
            pkg.contains("telegram") -> "Telegram"
            pkg.contains("paisa") || pkg.contains("gpay") -> "GPay"
            pkg.contains("phonepe") -> "PhonePe"
            pkg.contains("paytm") -> "Paytm"
            pkg.contains("messaging") || pkg.contains("mms") -> "Messages"
            else -> "Notification"
        }

        for (text in candidateTexts.distinct()) {
            Log.d("FinNLP", "Captured candidate from $appLabel ($pkg): $text")
            MainActivity.enqueueAndBroadcast(applicationContext, text, appLabel)
        }
    }
}
