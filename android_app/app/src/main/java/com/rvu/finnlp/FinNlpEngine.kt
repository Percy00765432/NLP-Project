package com.rvu.finnlp

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.regex.Pattern
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.roundToInt

data class NerSpan(
    val start: Int,
    val end: Int,
    val label: String
)

data class TransactionRecord(
    val id: String,
    val rawSms: String,
    val amount: Double,
    val type: String, // "debit" or "credit"
    val bank: String,
    val account: String,
    val date: String,
    val reference: String?,
    val vpa: String?,
    val merchant: String,
    val category: String,
    val synopsisCategory: String,
    val confidence: Double,
    val language: String,
    val isCodeMixed: Boolean,
    val source: String,
    val spans: List<NerSpan> = emptyList(),
    val timestamp: Long = System.currentTimeMillis()
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("rawSms", rawSms)
        put("amount", amount)
        put("type", type)
        put("bank", bank)
        put("account", account)
        put("date", date)
        put("reference", reference ?: "")
        put("vpa", vpa ?: "")
        put("merchant", merchant)
        put("category", category)
        put("synopsisCategory", synopsisCategory)
        put("confidence", confidence)
        put("language", language)
        put("isCodeMixed", isCodeMixed)
        put("source", source)
        put("timestamp", timestamp)
    }

    companion object {
        fun fromJson(obj: JSONObject): TransactionRecord = TransactionRecord(
            id = obj.optString("id"),
            rawSms = obj.optString("rawSms"),
            amount = obj.optDouble("amount", 0.0),
            type = obj.optString("type", "debit"),
            bank = obj.optString("bank", "Bank"),
            account = obj.optString("account", "----"),
            date = obj.optString("date", ""),
            reference = obj.optString("reference").takeIf { it.isNotEmpty() },
            vpa = obj.optString("vpa").takeIf { it.isNotEmpty() },
            merchant = obj.optString("merchant", "Merchant"),
            category = obj.optString("category", "shopping"),
            synopsisCategory = obj.optString("synopsisCategory", "Shopping"),
            confidence = obj.optDouble("confidence", 90.0),
            language = obj.optString("language", "English"),
            isCodeMixed = obj.optBoolean("isCodeMixed", false),
            source = obj.optString("source", "Manual"),
            timestamp = obj.optLong("timestamp", System.currentTimeMillis())
        )
    }
}

class FinNlpEngine(context: Context) {

    private val classes = mutableListOf<String>()
    private val intercepts = mutableListOf<Double>()
    private val wordWeights = HashMap<String, DoubleArray>()
    private val charWeights = HashMap<String, DoubleArray>()
    private val supportedLanguages = HashMap<String, String>()
    private val synopsisMap = HashMap<String, String>()
    private val indianBanks = HashMap<String, List<String>>()
    private val merchantLexicon = LinkedHashMap<String, Pair<String, String>>()
    private val indicGlossary = HashMap<String, String>()
    private val codeMixedLexicon = HashMap<String, String>()
    private val debitKeywords = mutableListOf<String>()
    private val creditKeywords = mutableListOf<String>()

    init {
        val jsonText = context.assets.open("finnlp_model.json").bufferedReader().use { it.readText() }
        val root = JSONObject(jsonText)

        val clsArr = root.getJSONArray("classes")
        for (i in 0 until clsArr.length()) classes.add(clsArr.getString(i))

        val intArr = root.getJSONArray("intercepts")
        for (i in 0 until intArr.length()) intercepts.add(intArr.getDouble(i))

        val wwObj = root.getJSONObject("word_weights")
        wwObj.keys().forEach { key ->
            val arr = wwObj.getJSONArray(key)
            wordWeights[key] = DoubleArray(arr.length()) { arr.getDouble(it) }
        }

        val cwObj = root.getJSONObject("char_weights")
        cwObj.keys().forEach { key ->
            val arr = cwObj.getJSONArray(key)
            charWeights[key] = DoubleArray(arr.length()) { arr.getDouble(it) }
        }

        val langObj = root.getJSONObject("supported_languages")
        langObj.keys().forEach { k -> supportedLanguages[k] = langObj.getString(k) }

        val synObj = root.getJSONObject("synopsis_category_map")
        synObj.keys().forEach { k -> synopsisMap[k] = synObj.getString(k) }

        val bankObj = root.getJSONObject("indian_banks")
        bankObj.keys().forEach { k ->
            val arr = bankObj.getJSONArray(k)
            indianBanks[k] = List(arr.length()) { arr.getString(it) }
        }

        val merchObj = root.getJSONObject("merchant_lexicon")
        val sortedMerchKeys = merchObj.keys().asSequence().toList().sortedByDescending { it.length }
        for (k in sortedMerchKeys) {
            val info = merchObj.getJSONObject(k)
            merchantLexicon[k] = Pair(info.getString("name"), info.getString("cat"))
        }

        val indObj = root.getJSONObject("indic_glossary")
        indObj.keys().forEach { k -> indicGlossary[k] = indObj.getString(k) }

        val cmObj = root.getJSONObject("code_mixed_lexicon")
        cmObj.keys().forEach { k -> codeMixedLexicon[k] = cmObj.getString(k) }

        val debArr = root.optJSONArray("debit_keywords") ?: JSONArray()
        for (i in 0 until debArr.length()) debitKeywords.add(debArr.getString(i).lowercase())

        val credArr = root.optJSONArray("credit_keywords") ?: JSONArray()
        for (i in 0 until credArr.length()) creditKeywords.add(credArr.getString(i).lowercase())
    }

    private fun detectLanguage(text: String): Pair<String, Boolean> {
        val counts = mutableMapOf("hi" to 0, "bn" to 0, "ta" to 0, "te" to 0, "kn" to 0)
        var latin = 0
        for (ch in text) {
            val cp = ch.code
            when {
                (cp in 0x41..0x5A) || (cp in 0x61..0x7A) -> latin++
                cp in 0x0900..0x097F -> counts["hi"] = counts["hi"]!! + 1
                cp in 0x0980..0x09FF -> counts["bn"] = counts["bn"]!! + 1
                cp in 0x0B80..0x0BFF -> counts["ta"] = counts["ta"]!! + 1
                cp in 0x0C00..0x0C7F -> counts["te"] = counts["te"]!! + 1
                cp in 0x0C80..0x0CFF -> counts["kn"] = counts["kn"]!! + 1
            }
        }
        val total = latin + counts.values.sum()
        if (total == 0) return Pair("en", false)
        val topEntry = counts.maxByOrNull { it.value }!!
        if (topEntry.value > 0) {
            val isCm = (latin.toDouble() / total >= 0.15) && (topEntry.value.toDouble() / total >= 0.10)
            return Pair(topEntry.key, isCm)
        }
        val extraCm = setOf("nimma", "inda", "agide", "mulaka", "unga", "irundhu", "aagiduchu")
        val tokens = Regex("[a-z]+").findAll(text.lowercase()).map { it.value }.toList()
        if (tokens.any { codeMixedLexicon.containsKey(it) || extraCm.contains(it) }) {
            return Pair("hinglish", true)
        }
        return Pair("en", false)
    }

    private fun normalizeText(text: String): String {
        val norm = text.replace(
            Regex("(?:₹|INR|Rs\\.?|रु\\.?|రూ\\.?|ரூ\\.?|৳|ರೂ\\.?)\\s*", RegexOption.IGNORE_CASE),
            "Rs. "
        )
        val aug = mutableListOf<String>()
        for (w in norm.split(Regex("\\s+"))) {
            val cw = w.trim('.', ',', ';', ':', '!', '(', ')', '[', ']', '{', '}', '"', '\'', '।', '|').lowercase()
            aug.add(w)
            indicGlossary[cw]?.let { aug.add(it) } ?: codeMixedLexicon[cw]?.let { aug.add(it) }
        }
        return aug.joinToString(" ").trim()
    }

    fun analyze(rawSms: String, source: String = "Manual"): TransactionRecord? {
        val raw = rawSms.trim()
        if (raw.isEmpty()) return null
        val lower = raw.lowercase()
        val (langCode, isCm) = detectLanguage(raw)
        val spans = mutableListOf<NerSpan>()

        // 1. Amount Extraction
        var amount: Double? = null
        val amtPatterns = listOf(
            Pattern.compile("(?:Rs\\.?|INR|₹|रु\\.?|రూ\\.?|ரூ\\.?|৳|ರೂ\\.?)\\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\\.[0-9]{1,2})?|[0-9]+(?:\\.[0-9]{1,2})?)", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\b([0-9]{1,3}(?:,[0-9]{2,3})+(?:\\.[0-9]{1,2})?|[0-9]+(?:\\.[0-9]{1,2})?)\\s*(?:rs\\.?|inr|rupees|rupaye)\\b", Pattern.CASE_INSENSITIVE)
        )
        for (pat in amtPatterns) {
            val m = pat.matcher(raw)
            if (m.find()) {
                amount = m.group(1)?.replace(",", "")?.toDoubleOrNull()
                if (amount != null) {
                    spans.add(NerSpan(m.start(), m.end(), "AMT"))
                    break
                }
            }
        }
        if (amount == null) return null

        // 2. Debit vs Credit
        var dPos = Int.MAX_VALUE
        var cPos = Int.MAX_VALUE
        for (k in debitKeywords) {
            val idx = lower.indexOf(k)
            if (idx != -1 && idx < dPos) dPos = idx
        }
        for (k in creditKeywords) {
            val idx = lower.indexOf(k)
            if (idx != -1 && idx < cPos) cPos = idx
        }
        val txnType = if (dPos <= cPos) "debit" else "credit"

        // 3. Bank
        var bank = "Bank"
        var bestBankPos = Int.MAX_VALUE
        for ((canon, aliases) in indianBanks) {
            for (al in aliases) {
                val idx = lower.indexOf(al.lowercase())
                if (idx != -1 && idx < bestBankPos) {
                    bestBankPos = idx
                    bank = canon
                }
            }
        }

        // 4. Account
        var account = "----"
        val acctMatcher = Pattern.compile(
            "(?:A/c|Acct|Account|Card|CC|खाता|खाते|ఖాతా|கணக்கு|অ্যাকাউন্ট|ಖಾತೆ|khate)\\s*(?:no\\.?|number)?\\s*(?:[xX*]+)?([0-9]{3,4})\\b",
            Pattern.CASE_INSENSITIVE
        ).matcher(raw)
        if (acctMatcher.find()) {
            account = acctMatcher.group(1) ?: "----"
            spans.add(NerSpan(acctMatcher.start(), acctMatcher.end(), "ACCT"))
        } else {
            val maskMatcher = Pattern.compile("\\b[xX*]{2,6}([0-9]{3,4})\\b").matcher(raw)
            if (maskMatcher.find()) {
                account = maskMatcher.group(1) ?: "----"
                spans.add(NerSpan(maskMatcher.start(), maskMatcher.end(), "ACCT"))
            }
        }

        // 5. Date
        var dateStr = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date())
        val dateMatcher = Pattern.compile("\\b([0-3][0-9][-/.][0-1][0-9][-/.](?:20)?[2-9][0-9])\\b").matcher(raw)
        if (dateMatcher.find()) {
            dateStr = dateMatcher.group(1) ?: dateStr
            spans.add(NerSpan(dateMatcher.start(), dateMatcher.end(), "DATE"))
        }

        // 6. VPA & Reference
        var vpa: String? = null
        val vpaMatcher = Pattern.compile("\\b([a-zA-Z0-9._-]+@[a-zA-Z]{2,15})\\b").matcher(raw)
        if (vpaMatcher.find()) {
            vpa = vpaMatcher.group(1)
            spans.add(NerSpan(vpaMatcher.start(), vpaMatcher.end(), "VPA"))
        }

        var reference: String? = null
        val refMatcher = Pattern.compile("(?:UPI\\s*Ref|IMPS\\s*Ref|NEFT\\s*Ref|Ref(?:\\s*No)?|संदर्भ)[\\s:.-]*([0-9]{9,14})\\b", Pattern.CASE_INSENSITIVE).matcher(raw)
        if (refMatcher.find()) {
            val cand = refMatcher.group(1)
            if (cand != null && !cand.startsWith("1800")) {
                reference = cand
                spans.add(NerSpan(refMatcher.start(), refMatcher.end(), "REF"))
            }
        } else {
            val twelveMatcher = Pattern.compile("\\b([0-9]{12})\\b").matcher(raw)
            if (twelveMatcher.find()) {
                val cand = twelveMatcher.group(1)
                if (cand != null && !cand.startsWith("1800")) {
                    reference = cand
                    spans.add(NerSpan(twelveMatcher.start(), twelveMatcher.end(), "REF"))
                }
            }
        }

        // 7. Merchant & Lexicon Hint
        var merchant: String? = null
        var lexCat: String? = null
        if (vpa != null) {
            val vpaClean = vpa.substringBefore("@").lowercase().replace(Regex("[0-9_.-]+$"), "")
            for ((k, info) in merchantLexicon) {
                if (vpaClean.contains(k.replace(" ", ""))) {
                    merchant = info.first
                    lexCat = info.second
                    break
                }
            }
        }
        if (merchant == null) {
            for ((k, info) in merchantLexicon) {
                if (lower.contains(k.lowercase())) {
                    merchant = info.first
                    lexCat = info.second
                    break
                }
            }
        }
        if (merchant == null) {
            val ctxMatcher = Pattern.compile("\\b(?:towards|from|to|at)\\s+([A-Z][A-Za-z0-9\\s.&'-]{2,25}?)(?:[.\\n;]|(?:\\s+(?:on|Ref|UPI|Bal|via|VPA|payment)))").matcher(raw)
            if (ctxMatcher.find()) {
                val cand = ctxMatcher.group(1)?.trim() ?: "Merchant"
                merchant = cand
                if (cand.split(Regex("\\s+")).size >= 2 && !cand.lowercase().contains("university") && !cand.lowercase().contains("bank")) {
                    lexCat = "transfer"
                }
            }
        }

        // 8. Trained Colab Subword TF-IDF + SVM/LogReg Ensemble Scoring
        val normText = normalizeText(raw).lowercase()
        val scores = intercepts.toDoubleArray()
        val words = Regex("\\b\\w\\w+\\b").findAll(normText).map { it.value }.toList()

        val wordCounts = HashMap<String, Int>()
        for (i in words.indices) {
            val u = words[i]
            wordCounts[u] = (wordCounts[u] ?: 0) + 1
            if (i + 1 < words.size) {
                val b = "$u ${words[i + 1]}"
                wordCounts[b] = (wordCounts[b] ?: 0) + 1
            }
        }
        for ((gram, cnt) in wordCounts) {
            val wVec = wordWeights[gram] ?: continue
            val tf = 1.0 + ln(cnt.toDouble())
            for (c in classes.indices) scores[c] += tf * wVec[c]
        }

        val charCounts = HashMap<String, Int>()
        for (w in words) {
            val padded = " $w "
            for (n in 3..5) {
                if (padded.length >= n) {
                    for (i in 0..(padded.length - n)) {
                        val cg = padded.substring(i, i + n)
                        charCounts[cg] = (charCounts[cg] ?: 0) + 1
                    }
                }
            }
        }
        for ((gram, cnt) in charCounts) {
            val wVec = charWeights[gram] ?: continue
            val tf = 1.0 + ln(cnt.toDouble())
            for (c in classes.indices) scores[c] += tf * wVec[c]
        }

        val maxScore = scores.maxOrNull() ?: 0.0
        val probs = DoubleArray(classes.size) { exp((scores[it] - maxScore) * 0.25) }
        var sumExp = probs.sum()
        for (i in probs.indices) probs[i] /= max(sumExp, 1e-9)

        if (lexCat != null) {
            val idx = classes.indexOf(lexCat)
            if (idx != -1) probs[idx] += 0.70
        }
        sumExp = probs.sum()
        for (i in probs.indices) probs[i] /= max(sumExp, 1e-9)

        var topIdx = 0
        for (i in 1 until probs.size) {
            if (probs[i] > probs[topIdx]) topIdx = i
        }
        val cat = classes[topIdx]
        val synCat = synopsisMap[cat] ?: "Shopping"
        val conf = ((probs[topIdx] * 1000.0).roundToInt() / 10.0)
        val langFull = supportedLanguages[langCode] ?: langCode

        return TransactionRecord(
            id = reference ?: "TXN-${System.currentTimeMillis()}",
            rawSms = raw,
            amount = amount,
            type = txnType,
            bank = bank,
            account = account,
            date = dateStr,
            reference = reference,
            vpa = vpa,
            merchant = merchant ?: (vpa?.substringBefore("@") ?: "Transaction"),
            category = cat,
            synopsisCategory = synCat,
            confidence = conf,
            language = langFull.substringBefore("(").trim(),
            isCodeMixed = isCm,
            source = source,
            spans = spans.sortedBy { it.start }
        )
    }
}
