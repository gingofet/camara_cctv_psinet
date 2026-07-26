package cl.cctvflow.camera.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import cl.cctvflow.camera.domain.Division
import cl.cctvflow.camera.domain.Turno
import cl.cctvflow.camera.ui.CCTVFlowUiState

@Composable
fun SelectionScreen(
    state: CCTVFlowUiState,
    onDivisionSelected: (Division) -> Unit,
    onTurnoSelected: (Turno) -> Unit,
    onSectorSelected: (String) -> Unit,
    onCameraSelected: (String) -> Unit,
    onSearchChanged: (String) -> Unit,
    onContinue: () -> Unit,
) {
    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(20.dp),
        ) {
            Text(
                text = "CCTVFlow Camera",
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                text = "Selecciona la cámara antes de iniciar la captura.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.height(20.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                SelectorMenu(
                    label = "División",
                    value = state.division.label,
                    options = Division.entries.map { it.label },
                    onSelected = { label ->
                        Division.entries
                            .firstOrNull { it.label == label }
                            ?.let(onDivisionSelected)
                    },
                    modifier = Modifier.weight(1f),
                )
                SelectorMenu(
                    label = "Turno",
                    value = state.turno.label,
                    options = Turno.entries.map { it.label },
                    onSelected = { label ->
                        Turno.entries
                            .firstOrNull { it.label == label }
                            ?.let(onTurnoSelected)
                    },
                    modifier = Modifier.weight(1f),
                )
            }

            Spacer(Modifier.height(12.dp))

            SelectorMenu(
                label = "Sector",
                value = state.selectedSector ?: "Seleccionar sector",
                options = state.sectors.map { it.name },
                onSelected = onSectorSelected,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = state.searchQuery,
                onValueChange = onSearchChanged,
                enabled = state.selectedSector != null,
                label = { Text("Buscar cámara") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(Modifier.height(12.dp))

            Text(
                text = when {
                    state.selectedSector == null -> "Selecciona un sector."
                    state.filteredCameras.isEmpty() -> "No se encontraron cámaras."
                    else -> "${state.filteredCameras.size} cámara(s)"
                },
                style = MaterialTheme.typography.labelLarge,
            )

            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(
                    items = state.filteredCameras,
                    key = { it },
                ) { camera ->
                    val selected = camera == state.selectedCamera
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onCameraSelected(camera) },
                        colors = CardDefaults.cardColors(
                            containerColor = if (selected) {
                                MaterialTheme.colorScheme.primaryContainer
                            } else {
                                MaterialTheme.colorScheme.surfaceVariant
                            },
                        ),
                    ) {
                        Text(
                            text = camera,
                            modifier = Modifier.padding(14.dp),
                        )
                    }
                }
            }

            Button(
                onClick = onContinue,
                enabled = state.canOpenCamera,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Abrir cámara")
            }
        }
    }
}

@Composable
private fun SelectorMenu(
    label: String,
    value: String,
    options: List<String>,
    onSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }

    Column(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
        )
        TextButton(
            onClick = { expanded = true },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(value)
        }
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option) },
                    onClick = {
                        expanded = false
                        onSelected(option)
                    },
                )
            }
        }
    }
}

