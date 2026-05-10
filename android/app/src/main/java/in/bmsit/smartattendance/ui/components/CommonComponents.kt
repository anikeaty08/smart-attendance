package `in`.bmsit.smartattendance.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun BrandHeader() {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Surface(
            border = BorderStroke(2.dp, Color.Black),
            color = Color.Transparent,
            shape = MaterialTheme.shapes.extraLarge,
            modifier = Modifier.padding(top = 2.dp),
        ) {
            Text("SA", modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp), fontWeight = FontWeight.Black)
        }
        Column {
            Text("Smart Attendance", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
            Text("Enrollment-first attendance", color = Color(0xFF666666))
        }
    }
}

@Composable
fun DashboardList(title: String, rows: List<String>) {
    ThinCard {
        Text(title, fontWeight = FontWeight.SemiBold)
        if (rows.isEmpty()) {
            Text("No records yet.", color = Color(0xFF666666))
        } else {
            rows.forEach { Text(it) }
        }
    }
}

@Composable
fun ThinCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = BorderStroke(1.dp, Color(0xFFD8D8D2)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            content()
        }
    }
}
