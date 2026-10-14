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
      <button @click="uploadAndGenerate" :disabled="!petFile">Generate Sticker</button>
    </div>

    <div v-if="taskId" class="task-box">
      <p>Task ID: {{ taskId }} — status: {{ taskStatus }}</p>
      <div v-if="resultUrl">
        <p>Result:</p>
        <img :src="resultUrl" alt="result" class="result-img" />
        <a :href="resultUrl" target="_blank">Open full result</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

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

function onPetFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  petFile.value = f
  const reader = new FileReader()
  reader.onload = (ev) => previewData.value = ev.target.result
  reader.readAsDataURL(f)
}

function onReferenceFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  referenceFile.value = f
  const reader = new FileReader()
  reader.onload = (ev) => referencePreviewData.value = ev.target.result
  reader.readAsDataURL(f)
}

async function uploadAndGenerate() {
  if (!petFile.value) return

  const petForm = new FormData()
  petForm.append('file', petFile.value)
  const petUploadRes = await axios.post('http://localhost:8000/api/v1/upload', petForm, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

  let refImageUrl = null
  if (referenceFile.value) {
    const refForm = new FormData()
    refForm.append('file', referenceFile.value)
    const refUploadRes = await axios.post('http://localhost:8000/api/v1/upload', refForm, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    refImageUrl = refUploadRes.data.url
  }

  const payload = {
    image_url: petUploadRes.data.url,
    reference_image_url: refImageUrl,
    top_text: `${styleTemplate.value === 'shocked' ? 'NO WAY' : styleTemplate.value === 'happy' ? 'BEST DAY EVER' : 'SO CUTE'}`,
    bottom_text: bottomText.value || (styleTemplate.value === 'shocked' ? 'THE PET DID THIS AGAIN' : styleTemplate.value === 'happy' ? 'THEY ARE THE BEST' : 'ME WHEN I SEE THEM')
  }
  if (topText.value) payload.top_text = topText.value

  const create = await axios.post('http://localhost:8000/api/v1/tasks', payload)
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
    if (['success', 'failed'].includes(res.data.status)) {
      clearInterval(interval)
    }
  }, 1500)
}
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
</style>
