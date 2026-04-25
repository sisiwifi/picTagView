<template>
  <div class="tag-color-picker" :class="{ 'tag-color-picker--disabled': disabled }">
    <div class="tag-color-picker__canvas-row">
      <div
        ref="panel"
        class="tag-color-picker__panel"
        :style="{ '--picker-hue': panelHueColor }"
        @pointerdown="startDrag('panel', $event)"
      >
        <span class="tag-color-picker__cursor" :style="panelCursorStyle"></span>
      </div>

      <div
        ref="hueTrack"
        class="tag-color-picker__slider tag-color-picker__slider--hue"
        @pointerdown="startDrag('hue', $event)"
      >
        <span class="tag-color-picker__thumb" :style="hueThumbStyle"></span>
      </div>

      <div
        ref="alphaTrack"
        class="tag-color-picker__slider tag-color-picker__slider--alpha"
        :class="{ 'tag-color-picker__slider--inactive': !alphaEnabled }"
        :style="{ '--alpha-color': alphaTrackColor }"
        @pointerdown="startDrag('alpha', $event)"
      >
        <span class="tag-color-picker__thumb" :style="alphaThumbStyle"></span>
      </div>
    </div>

    <div class="tag-color-picker__footer">
      <label class="tag-color-picker__hex-field">
        <span class="tag-color-picker__label">HEX</span>
        <input
          v-model.trim="hexInput"
          class="tag-color-picker__input"
          type="text"
          maxlength="9"
          spellcheck="false"
          :disabled="disabled"
          @focus="onHexFocus"
          @blur="onHexBlur"
          @keydown.enter.prevent="applyHexInput"
        >
      </label>

      <div class="tag-color-picker__meta">
        <span class="tag-color-picker__meta-label">透明度</span>
        <strong class="tag-color-picker__meta-value">{{ alphaText }}</strong>
      </div>
    </div>

    <p v-if="hexError" class="tag-color-picker__error">{{ hexError }}</p>
  </div>
</template>

<script>
import {
  alphaByteToPercent,
  clamp,
  hex8ToHsv,
  hsvToHex8,
  normalizeHex8,
  rgbHex,
  tryNormalizeHex8,
  withAlpha,
} from '../utils/tagColors'

export default {
  name: 'TagColorPicker',
  props: {
    modelValue: { type: String, default: '' },
    alphaEnabled: { type: Boolean, default: true },
    disabled: { type: Boolean, default: false },
    fallbackColor: { type: String, default: '#FF0000FF' },
  },
  emits: ['update:modelValue', 'change'],
  data() {
    const initialHex = this.resolveDisplayHex(this.modelValue)
    const initialState = hex8ToHsv(initialHex)
    return {
      hue: initialState.hue,
      saturation: initialState.saturation,
      value: initialState.value,
      alpha: this.alphaEnabled ? initialState.alpha : 255,
      hexInput: initialHex,
      hexError: '',
      editingHexInput: false,
      draggingTarget: '',
    }
  },
  computed: {
    currentHex() {
      return hsvToHex8(this.hue, this.saturation, this.value, this.alphaEnabled ? this.alpha : 255)
    },
    panelHueColor() {
      return rgbHex(hsvToHex8(this.hue, 100, 100, 255)) || '#FF0000'
    },
    alphaTrackColor() {
      return rgbHex(this.currentHex) || '#FF0000'
    },
    panelCursorStyle() {
      return {
        left: `${this.saturation}%`,
        top: `${100 - this.value}%`,
      }
    },
    hueThumbStyle() {
      return {
        top: `${(1 - (this.hue / 360)) * 100}%`,
      }
    },
    alphaThumbStyle() {
      return {
        top: `${(1 - (this.alpha / 255)) * 100}%`,
      }
    },
    alphaText() {
      return this.alphaEnabled ? `${alphaByteToPercent(this.alpha)}%` : 'FF'
    },
  },
  watch: {
    modelValue(nextValue) {
      if (this.editingHexInput) return
      this.syncFromValue(nextValue)
    },
    alphaEnabled(nextValue) {
      if (!nextValue) {
        this.alpha = 255
        this.emitCurrent()
        return
      }
      this.syncFromValue(this.modelValue)
      this.emitCurrent()
    },
  },
  beforeUnmount() {
    this.stopDragging()
  },
  methods: {
    resolveDisplayHex(value) {
      const normalized = normalizeHex8(value, { defaultAlpha: 'FF' }) || normalizeHex8(this.fallbackColor, { defaultAlpha: 'FF' }) || '#FF0000FF'
      return this.alphaEnabled ? normalized : withAlpha(normalized, 'FF')
    },
    syncFromValue(value) {
      const nextHex = this.resolveDisplayHex(value)
      const nextState = hex8ToHsv(nextHex)
      this.hue = nextState.hue
      this.saturation = nextState.saturation
      this.value = nextState.value
      this.alpha = this.alphaEnabled ? nextState.alpha : 255
      this.hexInput = nextHex
      this.hexError = ''
    },
    emitCurrent() {
      const nextHex = this.currentHex
      this.$emit('update:modelValue', nextHex)
      this.$emit('change', nextHex)
      if (!this.editingHexInput) {
        this.hexInput = nextHex
        this.hexError = ''
      }
    },
    startDrag(target, event) {
      if (this.disabled) return
      if (target === 'alpha' && !this.alphaEnabled) return
      event.preventDefault()
      this.draggingTarget = target
      this.updateFromPointer(target, event)
      window.addEventListener('pointermove', this.onPointerMove)
      window.addEventListener('pointerup', this.onPointerUp)
      window.addEventListener('pointercancel', this.onPointerUp)
    },
    onPointerMove(event) {
      if (!this.draggingTarget) return
      this.updateFromPointer(this.draggingTarget, event)
    },
    onPointerUp() {
      this.stopDragging()
    },
    stopDragging() {
      if (!this.draggingTarget) return
      this.draggingTarget = ''
      window.removeEventListener('pointermove', this.onPointerMove)
      window.removeEventListener('pointerup', this.onPointerUp)
      window.removeEventListener('pointercancel', this.onPointerUp)
    },
    updateFromPointer(target, event) {
      const refName = target === 'panel' ? 'panel' : (target === 'hue' ? 'hueTrack' : 'alphaTrack')
      const node = this.$refs[refName]
      if (!node) return
      const rect = node.getBoundingClientRect()
      const offsetX = clamp(event.clientX - rect.left, 0, rect.width)
      const offsetY = clamp(event.clientY - rect.top, 0, rect.height)

      if (target === 'panel') {
        this.saturation = rect.width ? (offsetX / rect.width) * 100 : 0
        this.value = rect.height ? 100 - ((offsetY / rect.height) * 100) : 0
      } else if (target === 'hue') {
        const ratio = rect.height ? (offsetY / rect.height) : 0
        this.hue = (1 - ratio) * 360
      } else {
        const ratio = rect.height ? (offsetY / rect.height) : 0
        this.alpha = Math.round((1 - ratio) * 255)
      }

      this.emitCurrent()
    },
    onHexFocus() {
      this.editingHexInput = true
      this.hexError = ''
    },
    onHexBlur() {
      this.applyHexInput()
    },
    applyHexInput() {
      const defaultAlpha = this.alphaEnabled ? this.currentHex.slice(7, 9) : 'FF'
      const normalized = tryNormalizeHex8(this.hexInput, { defaultAlpha })
      if (!normalized.valid || !normalized.value) {
        this.hexError = '请输入合法的 HEX 或 HEX8 颜色值'
        return
      }
      this.editingHexInput = false
      this.syncFromValue(this.alphaEnabled ? normalized.value : withAlpha(normalized.value, 'FF'))
      this.emitCurrent()
    },
  },
}
</script>

<style scoped lang="css">
.tag-color-picker {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.tag-color-picker--disabled {
  opacity: 0.65;
  pointer-events: none;
}

.tag-color-picker__canvas-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 22px 22px;
  gap: 0.75rem;
  align-items: stretch;
}

.tag-color-picker__panel {
  position: relative;
  min-height: 256px;
  border-radius: 22px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background:
    linear-gradient(180deg, rgba(0, 0, 0, 0), rgba(0, 0, 0, 1)),
    linear-gradient(90deg, rgba(255, 255, 255, 1), var(--picker-hue, #FF0000));
  cursor: crosshair;
}

.tag-color-picker__slider {
  position: relative;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  overflow: hidden;
  min-height: 256px;
  cursor: ns-resize;
}

.tag-color-picker__slider--hue {
  background: linear-gradient(
    180deg,
    #FF0000 0%,
    #FF00FF 16.66%,
    #0000FF 33.33%,
    #00FFFF 50%,
    #00FF00 66.66%,
    #FFFF00 83.33%,
    #FF0000 100%
  );
}

.tag-color-picker__slider--alpha {
  background:
    linear-gradient(180deg, var(--alpha-color, #FF0000), rgba(255, 255, 255, 0)),
    linear-gradient(45deg, rgba(148, 163, 184, 0.2) 25%, transparent 25%, transparent 50%, rgba(148, 163, 184, 0.2) 50%, rgba(148, 163, 184, 0.2) 75%, transparent 75%, transparent 100%);
  background-size: auto, 10px 10px;
}

.tag-color-picker__slider--inactive {
  filter: grayscale(1);
  cursor: not-allowed;
}

.tag-color-picker__cursor,
.tag-color-picker__thumb {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid #ffffff;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.25), 0 5px 12px rgba(15, 23, 42, 0.18);
  background: transparent;
  pointer-events: none;
}

.tag-color-picker__thumb {
  left: 50%;
}

.tag-color-picker__footer {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}

.tag-color-picker__hex-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.36rem;
}

.tag-color-picker__label,
.tag-color-picker__meta-label {
  color: #475569;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.tag-color-picker__input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 16px;
  padding: 0.82rem 0.95rem;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 700;
  text-transform: uppercase;
}

.tag-color-picker__meta {
  min-width: 112px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 16px;
  padding: 0.78rem 0.92rem;
  background: rgba(248, 250, 252, 0.92);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.tag-color-picker__meta-value {
  color: #0f172a;
  font-size: 0.96rem;
}

.tag-color-picker__error {
  margin: 0;
  border-radius: 999px;
  padding: 0.38rem 0.72rem;
  width: fit-content;
  background: rgba(254, 226, 226, 0.92);
  color: #991b1b;
  font-size: 0.74rem;
  font-weight: 700;
}

@media (max-width: 640px) {
  .tag-color-picker__canvas-row {
    grid-template-columns: minmax(0, 1fr) 18px 18px;
    gap: 0.55rem;
  }

  .tag-color-picker__panel,
  .tag-color-picker__slider {
    min-height: 210px;
  }

  .tag-color-picker__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .tag-color-picker__meta {
    min-width: 0;
  }
}
</style>