package com.rvu.finnlp

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            val fullBody = StringBuilder()
            var sender = "SMS"
            for (msg in messages) {
                sender = msg.displayOriginatingAddress ?: "SMS"
                fullBody.append(msg.displayMessageBody ?: "")
            }
            val body = fullBody.toString().trim()
            if (body.isNotEmpty()) {
                MainActivity.enqueueAndBroadcast(context, body, "SMS ($sender)")
            }
        }
    }
}
