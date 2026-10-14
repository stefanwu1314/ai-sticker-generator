<template>
  <div class="upload-editor">
    <div>
      <label>Upload pet image:</label>
      <input type="file" @change="onFileChange" accept="image/*" />
    </div>
    <div v-if="previewData" class="preview">
      <img :src="previewData" alt="preview" style="max-width:300px;display:block;margin-bottom:12px;" />
    </div>
    <div>
      <label>Top text</label>
      <input v-model="topText" />
    </div>
    <div>
      <label>Bottom text</label>
      <input v-model="bottomText" />
    </div>
    <div style="margin-top:12px">
      <button @click="uploadAndGenerate" :disabled="!file">Generate Sticker</button>
    </div>

    <div v-if="taskId" style="margin-top:16px">
      <p>Task ID: {{ taskId }} — status: {{ taskStatus }}</p>
      <div v-if="resultUrl">
        <p>Result:</p>
        <img :src="resultUrl" alt="result" style="max-width:320px;display:block;" />
        <a :href="resultUrl" target="_blank">Open full</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const file = ref(null)
const previewData = ref(null)
const topText = ref('')
const bottomText = ref('')
const taskId = ref(null)
const taskStatus = ref(null)
const resultUrl = ref(null)

function onFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  file.value = f
  const reader = new FileReader()
  reader.onload = (ev) => previewData.value = ev.target.result
  reader.readAsDataURL(f)
}

async function uploadAndGenerate() {
  if (!file.value) return
  const form = new FormData()
  form.append('file', file.value)
  const up = await axios.post('http://localhost:8000/api/v1/upload', form, { headers: { 'Content-Type': 'multipart/form-data' }})
  const imageUrl = up.data.url
  const create = await axios.post('http://localhost:8000/api/v1/tasks', { image_url: imageUrl, top_text: topText.value, bottom_text: bottomText.value })
  taskId.value = create.data.task_id
  pollStatus()
}

async function pollStatus() {
  if (!taskId.value) return
  taskStatus.value = 'pending'
  const interval = setInterval(async () => {
    const res = await axios.get(`http://localhost:8000/api/v1/tasks/${taskId.value}`)
    taskStatus.value = res.data.status
    if (res.data.result_url) {
      resultUrl.value = res.data.result_url
    }
    if (['success','failed'].includes(res.data.status)) {
      clearInterval(interval)
    }
  }, 1500)
}
</script>

<style scoped>
.upload-editor { border: 1px solid #eee; padding: 16px; border-radius: 8px }
input { display:block; margin:6px 0 12px; padding:6px }
button { padding:8px 12px }
</style>
