package com.rvu.finnlp

import android.Manifest
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.service.notification.NotificationListenerService
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.text.NumberFormat
import java.util.Locale
import kotlin.random.Random

val ALL_SYNOPSIS_CATEGORIES = listOf(
    "Food & Dining",
    "Shopping",
    "Travel & Transport",
    "Bills & Utilities",
    "Healthcare",
    "Education",
    "Investments & Wealth",
    "Entertainment & Lifestyle",
    "P2P Transfers",
    "Income & Salary"
)

class MainActivity : ComponentActivity() {

    private lateinit var engine: FinNlpEngine
    private val transactionsState = mutableStateListOf<TransactionRecord>()
    private val budgetsState = mutableStateMapOf<String, Double>()
    private val customVpaRulesState = mutableStateMapOf<String, String>()

    private val incomingReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            flushPendingQueue()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        engine = FinNlpEngine(applicationContext)
        loadCustomVpaRules()
        loadSavedLedger()
        loadSavedBudgets()

        val filter = IntentFilter("com.rvu.finnlp.INCOMING_BANK_MESSAGE")
        ContextCompat.registerReceiver(
            this,
            incomingReceiver,
            filter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )

        rebindAndScanNotifications()

        setContent {
            val darkColors = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                dynamicDarkColorScheme(LocalContext.current)
            } else {
                darkColorScheme(
                    primary = Color(0xFFA8C7FA),
                    onPrimary = Color(0xFF062E6F),
                    primaryContainer = Color(0xFF0842A0),
                    onPrimaryContainer = Color(0xFFD3E3FD),
                    secondaryContainer = Color(0xFF283546),
                    onSecondaryContainer = Color(0xFFC2D5EE),
                    background = Color(0xFF0E141B),
                    surface = Color(0xFF161F29),
                    surfaceVariant = Color(0xFF1E2936)
                )
            }

            MaterialTheme(colorScheme = darkColors) {
                FinNlpAppScreen(
                    transactions = transactionsState,
                    budgets = budgetsState,
                    engine = engine,
                    onAddTransaction = { record -> addRecordIfUnique(applyCustomVpaRule(record)) },
                    onDeleteTransaction = { id ->
                        transactionsState.removeAll { it.id == id }
                        saveLedger()
                    },
                    onUpdateCategory = { txn, newSynopsisCat ->
                        updateTransactionCategory(txn, newSynopsisCat)
                    },
                    onExportCsv = { shareTransactionsCsv() },
                    onClearAll = {
                        transactionsState.clear()
                        saveLedger()
                    },
                    onSaveBudgets = { updated ->
                        budgetsState.putAll(updated)
                        saveBudgets()
                    },
                    onOpenNotifSettings = {
                        startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                    },
                    onRequestSmsPermission = {
                        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECEIVE_SMS)
                            != PackageManager.PERMISSION_GRANTED
                        ) {
                            ActivityCompat.requestPermissions(
                                this,
                                arrayOf(Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS),
                                101
                            )
                        }
                    }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        rebindAndScanNotifications()
        flushPendingQueue()
    }

    private fun rebindAndScanNotifications() {
        try {
            NotificationListenerService.requestRebind(
                ComponentName(this, BankNotificationListener::class.java)
            )
            sendBroadcast(
                Intent("com.rvu.finnlp.SCAN_ACTIVE_NOTIFICATIONS").apply {
                    setPackage(packageName)
                }
            )
        } catch (_: Exception) {}
    }

    private fun flushPendingQueue() {
        val prefs = getSharedPreferences("finnlp_queue", Context.MODE_PRIVATE)
        val queueStr = prefs.getString("pending_list", null) ?: return
        prefs.edit().remove("pending_list").commit()
        val items = queueStr.split("|||").filter { it.isNotBlank() }
        for (item in items) {
            val parts = item.split(":::", limit = 2)
            if (parts.size == 2) {
                processIncomingSms(parts[1], parts[0])
            }
        }
    }

    private fun applyCustomVpaRule(record: TransactionRecord): TransactionRecord {
        val vpaKey = record.vpa?.lowercase()?.trim()
        val merchantKey = record.merchant.lowercase().trim()
        val learnedCat = (if (!vpaKey.isNullOrEmpty()) customVpaRulesState[vpaKey] else null)
            ?: customVpaRulesState[merchantKey]
        return if (learnedCat != null) {
            record.copy(synopsisCategory = learnedCat)
        } else {
            record
        }
    }

    private fun updateTransactionCategory(txn: TransactionRecord, newSynopsisCat: String) {
        val key = txn.vpa?.lowercase()?.trim()?.takeIf { it.isNotEmpty() }
            ?: txn.merchant.lowercase().trim()
        if (key.isNotEmpty()) {
            customVpaRulesState[key] = newSynopsisCat
            saveCustomVpaRules()
        }
        for (i in transactionsState.indices) {
            val item = transactionsState[i]
            val matchesKey = (!txn.vpa.isNullOrEmpty() && item.vpa.equals(txn.vpa, ignoreCase = true)) ||
                item.id == txn.id
            if (matchesKey) {
                transactionsState[i] = item.copy(synopsisCategory = newSynopsisCat)
            }
        }
        saveLedger()
    }

    private fun shareTransactionsCsv() {
        if (transactionsState.isEmpty()) return
        val sb = StringBuilder()
        sb.append("Date,Bank,Account,Merchant,VPA,Category,Type,Amount_INR,Language,Source,UPI_Ref\n")
        for (t in transactionsState) {
            val safeMerchant = t.merchant.replace(",", " ")
            sb.append("${t.date},${t.bank},XX${t.account},$safeMerchant,${t.vpa ?: ""},${t.synopsisCategory},${t.type},${t.amount},${t.language},${t.source},${t.reference ?: ""}\n")
        }
        val sendIntent = Intent(Intent.ACTION_SEND).apply {
            type = "text/csv"
            putExtra(Intent.EXTRA_SUBJECT, "FinNLP Expense Report (CSV)")
            putExtra(Intent.EXTRA_TEXT, sb.toString())
        }
        startActivity(Intent.createChooser(sendIntent, "Export Transactions CSV"))
    }

    private fun processIncomingSms(smsText: String, source: String) {
        val rawRecord = engine.analyze(smsText, source) ?: return
        addRecordIfUnique(applyCustomVpaRule(rawRecord))
    }

    private fun addRecordIfUnique(record: TransactionRecord): Boolean {
        if (record.reference != null && transactionsState.any { it.reference == record.reference }) {
            return false
        }
        if (transactionsState.any { it.rawSms == record.rawSms && it.amount == record.amount }) {
            return false
        }
        transactionsState.add(0, record)
        saveLedger()
        return true
    }

    private fun loadSavedLedger() {
        val prefs = getSharedPreferences("finnlp_store_v3", Context.MODE_PRIVATE)
        val raw = prefs.getString("ledger_json", "[]") ?: "[]"
        try {
            val arr = JSONArray(raw)
            transactionsState.clear()
            for (i in 0 until arr.length()) {
                transactionsState.add(TransactionRecord.fromJson(arr.getJSONObject(i)))
            }
        } catch (_: Exception) {}
    }

    private fun saveLedger() {
        val arr = JSONArray()
        transactionsState.forEach { arr.put(it.toJson()) }
        getSharedPreferences("finnlp_store_v3", Context.MODE_PRIVATE)
            .edit()
            .putString("ledger_json", arr.toString())
            .apply()
    }

    private fun loadCustomVpaRules() {
        val prefs = getSharedPreferences("finnlp_store_v3", Context.MODE_PRIVATE)
        val raw = prefs.getString("custom_vpa_rules_json", null) ?: return
        try {
            val obj = JSONObject(raw)
            obj.keys().forEach { k -> customVpaRulesState[k] = obj.getString(k) }
        } catch (_: Exception) {}
    }

    private fun saveCustomVpaRules() {
        val obj = JSONObject()
        customVpaRulesState.forEach { (k, v) -> obj.put(k, v) }
        getSharedPreferences("finnlp_store_v3", Context.MODE_PRIVATE)
            .edit()
            .putString("custom_vpa_rules_json", obj.toString())
            .apply()
    }

    private fun loadSavedBudgets() {
        val defaults = mapOf(
            "Food & Dining" to 5000.0,
            "Shopping" to 6000.0,
            "Travel & Transport" to 3000.0,
            "Bills & Utilities" to 4000.0,
            "Healthcare" to 3000.0,
            "Education" to 75000.0,
            "Investments & Wealth" to 20000.0
        )
        budgetsState.putAll(defaults)
        val prefs = getSharedPreferences("finnlp_store_v3", Context.MODE_PRIVATE)
        val raw = prefs.getString("budgets_json", null) ?: return
        try {
            val obj = JSONObject(raw)
            obj.keys().forEach { k -> budgetsState[k] = obj.optDouble(k, defaults[k] ?: 5000.0) }
        } catch (_: Exception) {}
    }

    private fun saveBudgets() {
        val obj = JSONObject()
        budgetsState.forEach { (k, v) -> obj.put(k, v) }
        getSharedPreferences("finnlp_store_v3", Context.MODE_PRIVATE)
            .edit()
            .putString("budgets_json", obj.toString())
            .apply()
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            unregisterReceiver(incomingReceiver)
        } catch (_: Exception) {}
    }

    companion object {
        fun enqueueAndBroadcast(context: Context, smsText: String, source: String) {
            val lower = smsText.lowercase()
            val hasCurrencyOrBank = lower.contains("rs") || lower.contains("inr") ||
                lower.contains("₹") || lower.contains("upi") || lower.contains("debited") ||
                lower.contains("credited") || lower.contains("a/c") || lower.contains("bank") ||
                lower.contains("डेबिट") || lower.contains("ಡೆಬಿಟ್") || lower.contains("டெபிட்") ||
                lower.contains("డెబిట్") || lower.contains("ডেবিট")
            if (!hasCurrencyOrBank) return

            val prefs = context.getSharedPreferences("finnlp_queue", Context.MODE_PRIVATE)
            val existing = prefs.getString("pending_list", "") ?: ""
            val entry = "$source:::$smsText"
            val updated = if (existing.isEmpty()) entry else "$existing|||$entry"
            prefs.edit().putString("pending_list", updated).commit()

            val intent = Intent("com.rvu.finnlp.INCOMING_BANK_MESSAGE").apply {
                setPackage(context.packageName)
                putExtra("sms_text", smsText)
                putExtra("source", source)
            }
            context.sendBroadcast(intent)
        }
    }
}

private val SAMPLE_PRESETS = listOf(
    "Hinglish — Swiggy Food" to "HDFC Bank Alert: Aapke A/c XX4248 se Rs.485.50 kat gaya for Swiggy payment on 28-04-2025 to swiggy@ybl. UPI Ref: 430298465323.",
    "English — RV University Tuition" to "SBI: INR 65,000.00 paid from A/c XX4821 on 14-08-2025 towards RV University Tuition Fee. VPA rvuniversity@sbi. Ref: 839201746512.",
    "Kannada (ಕನ್ನಡ) — Zepto Grocery" to "HDFC: ನಿಮ್ಮ ಖಾತೆ XX5059 ನಿಂದ Rs.530.87 ಡೆಬಿಟ್ ಆಗಿದೆ. ದಿನಾಂಕ 02-02-2025. zepto@ybl. Ref: 000359529957",
    "Kanglish — Myntra Shopping" to "ICICI Alert: Nimma A/c XX3319 inda Rs.2,499.00 Myntra ge UPI mulaka debit agide on 12-10-2025. VPA myntra@ybl. Ref: 617283940112",
    "Hindi (हिंदी) — Swiggy UPI" to "HDFC: आपके खाते XX4248 से Rs.268.73 डेबिट हुआ। दिनांक 28-04-2025। swiggy@ybl। संदर्भ: 430298465323",
    "Tamil (தமிழ்) — IRCTC Train" to "HDFC: உங்கள் கணக்கு XX6623 இல் இருந்து Rs.1,269.83 டெபிட் செய்யப்பட்டது. தேதி 03-03-2025. irctc@sbi. Ref: 822283029881",
    "Tanglish — Uber Ride" to "Axis Bank: Unga A/c XX7741 la irundhu Rs.340.00 Uber ku debit aagiduchu on 05-10-2025. VPA uber@axis. UPI Ref: 728394019283",
    "Telugu (తెలుగు) — Amazon" to "HDFC: మీ ఖాతా XX9731 నుండి Rs.1,403.06 డెబిట్ చేయబడింది. తేదీ 03-02-2025. amazon@ybl. Ref: 864907792778",
    "Bengali (বাংলা) — Apollo" to "HDFC: আপনার অ্যাকাউন্ট XX4385 থেকে Rs.940.23 ডেবিট হয়েছে। তারিখ 11-08-2025। apollo@hdfcbank। Ref: 764883136364",
    "English — Zerodha Investment" to "YES Bank: Rs.15,000.00 debited from A/c XX8306 on 07-03-2025. UPI/zerodha@hdfcbank. Ref: 906063582611"
)

private fun categoryEmoji(cat: String): String = when (cat) {
    "Food & Dining" -> "🍔"
    "Shopping" -> "🛍️"
    "Travel & Transport" -> "🚕"
    "Bills & Utilities" -> "⚡"
    "Healthcare" -> "💊"
    "Education" -> "🎓"
    "Investments & Wealth" -> "📈"
    "Entertainment & Lifestyle" -> "🎬"
    "P2P Transfers" -> "💸"
    "Income & Salary" -> "💰"
    else -> "💳"
}

private fun formatInr(amount: Double): String {
    val fmt = NumberFormat.getCurrencyInstance(Locale("en", "IN"))
    return fmt.format(amount)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FinNlpAppScreen(
    transactions: List<TransactionRecord>,
    budgets: Map<String, Double>,
    engine: FinNlpEngine,
    onAddTransaction: (TransactionRecord) -> Boolean,
    onDeleteTransaction: (String) -> Unit,
    onUpdateCategory: (TransactionRecord, String) -> Unit,
    onExportCsv: () -> Unit,
    onClearAll: () -> Unit,
    onSaveBudgets: (Map<String, Double>) -> Unit,
    onOpenNotifSettings: () -> Unit,
    onRequestSmsPermission: () -> Unit
) {
    var currentTab by remember { mutableIntStateOf(0) }
    val snackbarHostState = remember { SnackbarHostState() }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = "FinNLP",
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 22.sp
                    )
                },
                actions = {
                    if (transactions.isNotEmpty()) {
                        IconButton(onClick = onExportCsv) {
                            Icon(
                                imageVector = Icons.Outlined.IosShare,
                                contentDescription = "Export CSV"
                            )
                        }
                    }
                }
            )
        },
        floatingActionButton = {
            if (currentTab == 0) {
                ExtendedFloatingActionButton(
                    onClick = { currentTab = 1 },
                    icon = { Icon(Icons.Outlined.Add, contentDescription = null) },
                    text = { Text("Add SMS", fontWeight = FontWeight.Bold) },
                    shape = RoundedCornerShape(22.dp)
                )
            }
        },
        bottomBar = {
            NavigationBar(tonalElevation = 6.dp) {
                NavigationBarItem(
                    selected = currentTab == 0,
                    onClick = { currentTab = 0 },
                    icon = { Icon(Icons.Outlined.AccountBalanceWallet, contentDescription = null) },
                    label = { Text("Overview") }
                )
                NavigationBarItem(
                    selected = currentTab == 1,
                    onClick = { currentTab = 1 },
                    icon = { Icon(Icons.Outlined.AutoAwesome, contentDescription = null) },
                    label = { Text("Analyze") }
                )
                NavigationBarItem(
                    selected = currentTab == 2,
                    onClick = { currentTab = 2 },
                    icon = { Icon(Icons.Outlined.Tune, contentDescription = null) },
                    label = { Text("Settings") }
                )
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (currentTab) {
                0 -> OverviewTab(
                    transactions = transactions,
                    budgets = budgets,
                    engine = engine,
                    onDeleteTransaction = onDeleteTransaction,
                    onUpdateCategory = onUpdateCategory,
                    onExportCsv = onExportCsv,
                    onClearAll = onClearAll
                )
                1 -> AnalyzeTab(
                    engine = engine,
                    onAddTransaction = onAddTransaction,
                    snackbarHostState = snackbarHostState
                )
                2 -> SettingsTab(
                    budgets = budgets,
                    onSaveBudgets = onSaveBudgets,
                    onOpenNotifSettings = onOpenNotifSettings,
                    onRequestSmsPermission = onRequestSmsPermission,
                    snackbarHostState = snackbarHostState
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OverviewTab(
    transactions: List<TransactionRecord>,
    budgets: Map<String, Double>,
    engine: FinNlpEngine,
    onDeleteTransaction: (String) -> Unit,
    onUpdateCategory: (TransactionRecord, String) -> Unit,
    onExportCsv: () -> Unit,
    onClearAll: () -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedCategoryFilter by remember { mutableStateOf("All") }
    var inspectedTxn by remember { mutableStateOf<TransactionRecord?>(null) }

    val totalDebit = transactions.filter { it.type == "debit" }.sumOf { it.amount }
    val totalCredit = transactions.filter { it.type == "credit" }.sumOf { it.amount }
    val catTotals = transactions
        .filter { it.type == "debit" }
        .groupBy { it.synopsisCategory }
        .mapValues { entry -> entry.value.sumOf { it.amount } }
        .toList()
        .sortedByDescending { it.second }

    val topCategory = catTotals.firstOrNull()?.first ?: "—"

    val filteredTransactions = remember(transactions, searchQuery, selectedCategoryFilter) {
        transactions.filter { txn ->
            val matchesCat = selectedCategoryFilter == "All" || txn.synopsisCategory == selectedCategoryFilter
            val q = searchQuery.trim().lowercase()
            val matchesSearch = q.isEmpty() ||
                txn.merchant.lowercase().contains(q) ||
                txn.bank.lowercase().contains(q) ||
                txn.synopsisCategory.lowercase().contains(q) ||
                (txn.vpa?.lowercase()?.contains(q) == true) ||
                txn.rawSms.lowercase().contains(q)
            matchesCat && matchesSearch
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Material 3 Expressive Hero Spend Card
        item {
            Card(
                shape = RoundedCornerShape(32.dp),
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.Transparent)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(
                            Brush.linearGradient(
                                listOf(Color(0xFF1A2D4C), Color(0xFF121D31))
                            )
                        )
                        .padding(24.dp)
                ) {
                    Column {
                        Text(
                            text = "Total Spent",
                            color = MaterialTheme.colorScheme.onSecondaryContainer,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = formatInr(totalDebit),
                            color = Color.White,
                            fontSize = 36.sp,
                            fontWeight = FontWeight.ExtraBold
                        )
                        Spacer(modifier = Modifier.height(18.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Surface(
                                shape = RoundedCornerShape(18.dp),
                                color = Color.White.copy(alpha = 0.07f),
                                modifier = Modifier.weight(1f)
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text("Credits", color = Color(0xFF94A3B8), fontSize = 11.sp)
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = formatInr(totalCredit),
                                        color = Color(0xFF6DD58C),
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 15.sp
                                    )
                                }
                            }
                            Surface(
                                shape = RoundedCornerShape(18.dp),
                                color = Color.White.copy(alpha = 0.07f),
                                modifier = Modifier.weight(1f)
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text("Top Category", color = Color(0xFF94A3B8), fontSize = 11.sp)
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = topCategory,
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 15.sp,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // Category Budget Bars (only shown when user has expenses)
        if (catTotals.isNotEmpty()) {
            item {
                Text(
                    text = "Category Breakdown",
                    fontWeight = FontWeight.Bold,
                    fontSize = 17.sp
                )
            }
            item {
                ElevatedCard(
                    shape = RoundedCornerShape(28.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        for ((cat, spent) in catTotals) {
                            val budget = budgets[cat] ?: 10000.0
                            val progress = (spent / budget).coerceIn(0.0, 1.0).toFloat()
                            val isOver = spent > budget
                            Column {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = "${categoryEmoji(cat)} $cat",
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 14.sp
                                    )
                                    Text(
                                        text = "${formatInr(spent)} / ${formatInr(budget)}",
                                        color = if (isOver) Color(0xFFFF897D) else MaterialTheme.colorScheme.onSurfaceVariant,
                                        fontSize = 12.sp
                                    )
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                LinearProgressIndicator(
                                    progress = { progress },
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(8.dp)
                                        .clip(CircleShape),
                                    color = if (isOver) Color(0xFFFF897D) else MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }
            }
        }

        // Search & Filter Chips (shown when transactions exist)
        if (transactions.isNotEmpty()) {
            item {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Search merchant, bank, VPA, or SMS...") },
                    leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null) },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Outlined.Clear, contentDescription = "Clear search")
                            }
                        }
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(20.dp),
                    modifier = Modifier.fillMaxWidth()
                )
            }

            item {
                val filterOptions = remember(transactions) {
                    listOf("All") + transactions.map { it.synopsisCategory }.distinct()
                }
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(filterOptions) { cat ->
                        FilterChip(
                            selected = selectedCategoryFilter == cat,
                            onClick = { selectedCategoryFilter = cat },
                            label = {
                                Text(
                                    text = if (cat == "All") "All (${transactions.size})"
                                    else "${categoryEmoji(cat)} $cat"
                                )
                            },
                            shape = RoundedCornerShape(16.dp)
                        )
                    }
                }
            }
        }

        // Recent Transactions Header
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Recent Transactions",
                    fontWeight = FontWeight.Bold,
                    fontSize = 17.sp
                )
                if (transactions.isNotEmpty()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        TextButton(onClick = onExportCsv) {
                            Text("Export CSV")
                        }
                        TextButton(onClick = onClearAll) {
                            Text("Clear All", color = Color(0xFFFF897D))
                        }
                    }
                }
            }
        }

        // Clean Empty State or Transaction Cards
        if (transactions.isEmpty()) {
            item {
                ElevatedCard(
                    shape = RoundedCornerShape(28.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 42.dp, horizontal = 24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Surface(
                            shape = RoundedCornerShape(20.dp),
                            color = MaterialTheme.colorScheme.secondaryContainer,
                            modifier = Modifier.size(60.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text("✨", fontSize = 26.sp)
                            }
                        }
                        Spacer(modifier = Modifier.height(14.dp))
                        Text(
                            text = "No transactions yet",
                            fontWeight = FontWeight.Bold,
                            fontSize = 17.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Incoming bank SMS and Instagram/WhatsApp/Gmail alerts will appear here automatically, or tap + Add SMS.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 13.sp
                        )
                    }
                }
            }
        } else {
            items(filteredTransactions, key = { it.id }) { txn ->
                ElevatedCard(
                    shape = RoundedCornerShape(24.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { inspectedTxn = txn }
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.weight(1f)
                        ) {
                            Surface(
                                shape = RoundedCornerShape(16.dp),
                                color = MaterialTheme.colorScheme.secondaryContainer,
                                modifier = Modifier.size(46.dp)
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Text(categoryEmoji(txn.synopsisCategory), fontSize = 20.sp)
                                }
                            }
                            Spacer(modifier = Modifier.width(14.dp))
                            Column {
                                Text(
                                    text = txn.merchant,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 15.sp,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Text(
                                    text = "${txn.bank} (XX${txn.account}) • ${txn.date}",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontSize = 12.sp
                                )
                                Text(
                                    text = "${txn.language} • ${txn.source} • Tap to inspect",
                                    color = MaterialTheme.colorScheme.primary,
                                    fontSize = 11.sp
                                )
                            }
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            val isDebit = txn.type == "debit"
                            Text(
                                text = "${if (isDebit) "-" else "+"}${formatInr(txn.amount)}",
                                fontWeight = FontWeight.ExtraBold,
                                fontSize = 15.sp,
                                color = if (isDebit) MaterialTheme.colorScheme.onSurface else Color(0xFF6DD58C)
                            )
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = MaterialTheme.colorScheme.secondaryContainer,
                                modifier = Modifier.padding(top = 4.dp)
                            ) {
                                Text(
                                    text = txn.synopsisCategory,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
        item { Spacer(modifier = Modifier.height(72.dp)) }
    }

    // Modal Bottom Sheet to inspect NER spans, recategorize (teach VPA), or delete single transaction
    val currentInspected = inspectedTxn
    if (currentInspected != null) {
        val reanalyzed = remember(currentInspected) {
            engine.analyze(currentInspected.rawSms, currentInspected.source) ?: currentInspected
        }
        ModalBottomSheet(
            onDismissRequest = { inspectedTxn = null },
            shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
                    .padding(bottom = 32.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = currentInspected.merchant,
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 20.sp
                        )
                        Text(
                            text = "${currentInspected.bank} (XX${currentInspected.account}) • ${currentInspected.date}",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    IconButton(
                        onClick = {
                            onDeleteTransaction(currentInspected.id)
                            inspectedTxn = null
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Delete,
                            contentDescription = "Delete Transaction",
                            tint = Color(0xFFFF897D)
                        )
                    }
                }

                // Highlighted NER Spans
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    val annotated = buildAnnotatedString {
                        var cursor = 0
                        for (span in reanalyzed.spans) {
                            if (span.start < cursor || span.end > reanalyzed.rawSms.length) continue
                            append(reanalyzed.rawSms.substring(cursor, span.start))
                            withStyle(
                                SpanStyle(
                                    color = Color(0xFFA8C7FA),
                                    background = Color(0xFF0842A0).copy(alpha = 0.45f),
                                    fontWeight = FontWeight.Bold
                                )
                            ) {
                                append(" ${reanalyzed.rawSms.substring(span.start, span.end)} [${span.label}] ")
                            }
                            cursor = span.end
                        }
                        if (cursor < reanalyzed.rawSms.length) {
                            append(reanalyzed.rawSms.substring(cursor))
                        }
                    }
                    Text(
                        text = annotated,
                        fontSize = 13.sp,
                        lineHeight = 20.sp,
                        modifier = Modifier.padding(14.dp)
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    EntityTile("Amount", "${formatInr(currentInspected.amount)} (${currentInspected.type.uppercase()})", Modifier.weight(1f))
                    EntityTile("UPI Ref / VPA", currentInspected.vpa ?: (currentInspected.reference ?: "—"), Modifier.weight(1f))
                }

                Text(
                    text = "Change Category (Remembers this Merchant / VPA):",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(ALL_SYNOPSIS_CATEGORIES) { cat ->
                        FilterChip(
                            selected = currentInspected.synopsisCategory == cat,
                            onClick = {
                                onUpdateCategory(currentInspected, cat)
                                inspectedTxn = currentInspected.copy(synopsisCategory = cat)
                            },
                            label = { Text("${categoryEmoji(cat)} $cat") },
                            shape = RoundedCornerShape(14.dp)
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalyzeTab(
    engine: FinNlpEngine,
    onAddTransaction: (TransactionRecord) -> Boolean,
    snackbarHostState: SnackbarHostState
) {
    var smsInput by remember { mutableStateOf("") }
    var lastResult by remember { mutableStateOf<TransactionRecord?>(null) }
    var expanded by remember { mutableStateOf(false) }
    var selectedPresetLabel by remember { mutableStateOf("Choose sample language preset...") }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            ElevatedCard(
                shape = RoundedCornerShape(28.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Text(
                        text = "Analyze or Simulate SMS",
                        fontWeight = FontWeight.Bold,
                        fontSize = 17.sp
                    )

                    ExposedDropdownMenuBox(
                        expanded = expanded,
                        onExpandedChange = { expanded = !expanded }
                    ) {
                        OutlinedTextField(
                            value = selectedPresetLabel,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Multilingual Preset") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier
                                .menuAnchor()
                                .fillMaxWidth()
                        )
                        ExposedDropdownMenu(
                            expanded = expanded,
                            onDismissRequest = { expanded = false }
                        ) {
                            SAMPLE_PRESETS.forEach { (label, sms) ->
                                DropdownMenuItem(
                                    text = { Text(label) },
                                    onClick = {
                                        selectedPresetLabel = label
                                        smsInput = sms
                                        expanded = false
                                    }
                                )
                            }
                        }
                    }

                    OutlinedTextField(
                        value = smsInput,
                        onValueChange = { smsInput = it },
                        label = { Text("Bank / UPI SMS Text") },
                        placeholder = { Text("Paste any bank or UPI SMS here...") },
                        minLines = 3,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Button(
                            onClick = {
                                val res = engine.analyze(smsInput, "Manual")
                                if (res != null) {
                                    lastResult = res
                                    onAddTransaction(res)
                                }
                            },
                            shape = RoundedCornerShape(50),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Extract & Save", fontWeight = FontWeight.Bold)
                        }

                        FilledTonalButton(
                            onClick = {
                                val (label, sample) = SAMPLE_PRESETS.random()
                                val randRef = Random.nextLong(100000000000L, 999999999999L)
                                val randomized = sample.replace(Regex("Ref:\\s*[0-9]+"), "Ref: $randRef")
                                selectedPresetLabel = label
                                smsInput = randomized
                                val res = engine.analyze(randomized, "Simulated")
                                if (res != null) {
                                    lastResult = res
                                    onAddTransaction(res)
                                }
                            },
                            shape = RoundedCornerShape(50),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Simulate SMS", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        item {
            AnimatedVisibility(visible = lastResult != null) {
                val res = lastResult ?: return@AnimatedVisibility
                ElevatedCard(
                    shape = RoundedCornerShape(28.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Extracted Entities", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                            Surface(
                                shape = CircleShape,
                                color = MaterialTheme.colorScheme.primaryContainer
                            ) {
                                Text(
                                    text = "${res.synopsisCategory} (${res.confidence}%)",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                                )
                            }
                        }

                        // Highlighted NER Spans
                        Surface(
                            shape = RoundedCornerShape(16.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            val annotated = buildAnnotatedString {
                                var cursor = 0
                                for (span in res.spans) {
                                    if (span.start < cursor || span.end > res.rawSms.length) continue
                                    append(res.rawSms.substring(cursor, span.start))
                                    withStyle(
                                        SpanStyle(
                                            color = Color(0xFFA8C7FA),
                                            background = Color(0xFF0842A0).copy(alpha = 0.45f),
                                            fontWeight = FontWeight.Bold
                                        )
                                    ) {
                                        append(" ${res.rawSms.substring(span.start, span.end)} [${span.label}] ")
                                    }
                                    cursor = span.end
                                }
                                if (cursor < res.rawSms.length) {
                                    append(res.rawSms.substring(cursor))
                                }
                            }
                            Text(
                                text = annotated,
                                fontSize = 13.sp,
                                lineHeight = 20.sp,
                                modifier = Modifier.padding(14.dp)
                            )
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            EntityTile("Amount", "${formatInr(res.amount)} (${res.type.uppercase()})", Modifier.weight(1f))
                            EntityTile("Merchant", res.merchant, Modifier.weight(1f))
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            EntityTile("Bank & Account", "${res.bank} (XX${res.account})", Modifier.weight(1f))
                            EntityTile("Language", "${res.language}${if (res.isCodeMixed) " (Code-Mixed)" else ""}", Modifier.weight(1f))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun EntityTile(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(label, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.height(2.dp))
            Text(value, fontWeight = FontWeight.Bold, fontSize = 13.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
fun SettingsTab(
    budgets: Map<String, Double>,
    onSaveBudgets: (Map<String, Double>) -> Unit,
    onOpenNotifSettings: () -> Unit,
    onRequestSmsPermission: () -> Unit,
    snackbarHostState: SnackbarHostState
) {
    val editableBudgets = remember(budgets) {
        mutableStateMapOf<String, String>().apply {
            budgets.forEach { (k, v) -> put(k, v.toInt().toString()) }
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            ElevatedCard(
                shape = RoundedCornerShape(28.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("Wi-Fi Notification Auto-Capture", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text(
                        "Captures bank & UPI messages from Instagram, WhatsApp, Gmail, Telegram, or Messages over Wi-Fi without needing a SIM card.",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Button(
                        onClick = onOpenNotifSettings,
                        shape = RoundedCornerShape(50),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Enable Notification Access", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        item {
            ElevatedCard(
                shape = RoundedCornerShape(28.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("Cellular SMS Receiver", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text(
                        "Automatically intercepts incoming bank SMS messages when a SIM card is active.",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    FilledTonalButton(
                        onClick = onRequestSmsPermission,
                        shape = RoundedCornerShape(50),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Grant SMS Permission", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        item {
            ElevatedCard(
                shape = RoundedCornerShape(28.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("Monthly Category Budgets (₹)", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    editableBudgets.keys.sorted().forEach { cat ->
                        OutlinedTextField(
                            value = editableBudgets[cat] ?: "5000",
                            onValueChange = { editableBudgets[cat] = it },
                            label = { Text("${categoryEmoji(cat)} $cat") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            singleLine = true,
                            shape = RoundedCornerShape(14.dp),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    Button(
                        onClick = {
                            val parsed = editableBudgets.mapValues { it.value.toDoubleOrNull() ?: 5000.0 }
                            onSaveBudgets(parsed)
                        },
                        shape = RoundedCornerShape(50),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Save Budgets", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
