import * as _Slider from '@radix-ui/react-slider'
import { useState } from 'react'
import { Tooltip } from '../tooltip/tooltip'
import styles from './slider.module.scss'

interface SliderProps {
  label: string
  description: string
  settings?: {
    min: number
    max: number
    step: number
    defaultValue: number
  }
}

export const Slider = ({
  label,
  description,
  settings = { min: 0, max: 1, step: 0.01, defaultValue: 0.5 },
}: SliderProps) => {
  const [value, setValue] = useState<number>(settings.defaultValue)

  return (
    <div>
      <label className={styles.label}>{label}</label>
      <_Slider.Root
        className={styles.sliderRoot}
        defaultValue={[settings.defaultValue]}
        min={settings.min}
        max={settings.max}
        step={settings.step}
        onValueChange={(values) => setValue(values[0])}
      >
        <_Slider.Track className={styles.sliderTrack}>
          <_Slider.Range className={styles.sliderRange} />
        </_Slider.Track>
        <_Slider.Thumb className={styles.sliderThumb}>
          <span className={styles.sliderValue}>{value}</span>
        </_Slider.Thumb>
      </_Slider.Root>
      <span className={styles.description}>{description}</span>
    </div>
  )
}

interface PlaybackSliderProps {
  value: number
  onValueChange: (value: number) => void
  onValueCommit: (value: number) => void
  settings?: {
    min: number
    max: number
    step: number
    defaultValue: number
  }
  tooltip: string
}

export const PlaybackSlider = ({
  value,
  onValueChange,
  onValueCommit,
  settings = { min: 0, max: 1, step: 0.01, defaultValue: 0.5 },
  tooltip,
}: PlaybackSliderProps) => {
  const [active, setActive] = useState(false)

  return (
    <div>
      <_Slider.Root
        className={styles.playbackSliderRoot}
        defaultValue={[settings.defaultValue]}
        min={settings.min}
        max={settings.max}
        step={settings.step}
        value={[value]}
        onValueChange={(values) => onValueChange(values[0])}
        onValueCommit={(values) => onValueCommit(values[0])}
        onPointerDown={() => setActive(true)}
        onPointerUp={() => setActive(false)}
        onPointerLeave={() => {
          if (active) {
            onValueCommit(value)
          }
        }}
      >
        <_Slider.Track className={styles.sliderTrack}>
          <_Slider.Range className={styles.sliderRange} />
        </_Slider.Track>
        <Tooltip content={tooltip}>
          <_Slider.Thumb className={styles.sliderThumb} />
        </Tooltip>
      </_Slider.Root>
    </div>
  )
}
