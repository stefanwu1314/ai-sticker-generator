<template>
  <div class="upload-editor">
    <div class="field-group">
      <label>Upload your pet image</label>
      <input type="file" @change="onPetFileChange" accept="image/*" />
    </div>

    <div class="field-group">
      <label>Upload reference meme / style image (optional)</label>
      <input type="file" @change="onReferenceFileChange" accept="image/*" />
    </div>

    <div v-if="previewData" class="preview">
      <img :src="previewData" alt="pet preview" />
    </div>
    <div v-if="referencePreviewData" class="preview reference-preview">
      <img :src="referencePreviewData" alt="reference preview" />
    </div>

    <div class="field-group">
      <label>Style template</label>
      <select v-model="styleTemplate">
        <option value="cute">Cute animal meme</option>
        <option value="shocked">Shocked animal meme</option>
        <option value="happy">Happy animal meme</option>
      </select>
    </div>

    <div class="field-group">
      <label>Top text</label>
      <input v-model="topText" placeholder="e.g. WHEN I SEE FOOD" />
    </div>
    <div class="field-group">
      <label>Bottom text</label>
      <input v-model="bottomText" placeholder="e.g. ME: *runs in circles*" />
    </div>

    <div class="actions">
      <button @click="uploadAndGenerate" :disabled="!petFile || generating">
        {{ generating ? 'Generating...' : 'Generate Sticker' }}
      </button>
    </div>

    <div v-if="taskId" class="task-box">
      <p>Task ID: {{ taskId }} — status: {{ taskStatus }}</p>
      <div v-if="taskError" class="error">{{ taskError }}</div>
      <div v-if="resultUrl">
        <p>Result:</p>
        <img :src="resultUrl" alt="result" class="result-img" />
        <a :href="resultUrl" target="_blank" rel="noopener">Open full result</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const petFile = ref(null)
const referenceFile = ref(null)
const previewData = ref(null)
const referencePreviewData = ref(null)
const topText = ref('')
const bottomText = ref('')
const styleTemplate = ref('cute')
const taskId = ref(null)
const taskStatus = ref(null)
const resultUrl = ref(null)
const taskError = ref(null)
const generating = ref(false)

let pollTimer = null

function onPetFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  petFile.value = f
  const reader = new FileReader()
  reader.onload = (ev) => (previewData.value = ev.target.result)
  reader.readAsDataURL(f)
}

function onReferenceFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  referenceFile.value = f
  const reader = new FileReader()
  reader.onload = (ev) => (referencePreviewData.value = ev.target.result)
  reader.readAsDataURL(f)
}

function defaultTop(template) {
  return template === 'shocked' ? 'NO WAY' : template === 'happy' ? 'BEST DAY EVER' : 'SO CUTE'
}

function defaultBottom(template) {
  return template === 'shocked'
    ? 'THE PET DID THIS AGAIN'
    : template === 'happy'
      ? 'THEY ARE THE BEST'
      : 'ME WHEN I SEE THEM'
}

async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await axios.post(`${API_BASE}/api/v1/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

async function uploadAndGenerate() {
  if (!petFile.value || generating.value) return
  generating.value = true
  taskError.value = null
  resultUrl.value = null
  try {
    const pet = await uploadImage(petFile.value)
    let refData = null
    if (referenceFile.value) {
      refData = await uploadImage(referenceFile.value)
    }

    const payload = {
      // internal_url is reachable by the worker inside the docker network
      image_url: pet.internal_url,
      reference_image_url: refData ? refData.internal_url : null,
      top_text: topText.value || defaultTop(styleTemplate.value),
      bottom_text: bottomText.value || defaultBottom(styleTemplate.value)
    }

    const create = await axios.post(`${API_BASE}/api/v1/tasks`, payload)
    taskId.value = create.data.task_id
    taskStatus.value = 'pending'
    pollStatus()
  } catch (e) {
    taskError.value = e?.response?.data?.detail || e.message
    generating.value = false
  }
}

function pollStatus() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/v1/tasks/${taskId.value}`)
      taskStatus.value = res.data.status
      if (res.data.result_url) {
        resultUrl.value = res.data.result_url
      }
      if (res.data.error) {
        taskError.value = res.data.error
      }
      if (['success', 'failed'].includes(res.data.status)) {
        stopPolling()
        generating.value = false
      }
    } catch (e) {
      stopPolling()
      generating.value = false
      taskError.value = e.message
    }
  }, 1500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onUnmounted(stopPolling)
</script>

<style scoped>
.upload-editor {
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 20px;
  background: #fff;
}
.field-group {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.preview {
  margin: 10px 0;
}
.preview img {
  max-width: 280px;
  max-height: 280px;
  border-radius: 10px;
}
.reference-preview {
  border: 1px dashed #ddd;
  padding: 8px;
  display: inline-block;
}
.actions {
  margin-top: 12px;
}
button {
  background: #0a84ff;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 14px;
  cursor: pointer;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.task-box {
  margin-top: 18px;
  border-top: 1px solid #eee;
  padding-top: 12px;
}
.result-img {
  max-width: 320px;
  border-radius: 10px;
  display: block;
  margin: 8px 0;
}
.error {
  color: #d33;
  margin: 8px 0;
  word-break: break-all;
}
</style>
