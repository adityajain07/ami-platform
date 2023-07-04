export type ServerOccurrence = any // TODO: Update this type

export class Occurrence {
  private readonly _occurrence: ServerOccurrence
  private readonly _images: { src: string }[] = []

  public constructor(occurrence: ServerOccurrence) {
    this._occurrence = occurrence

    this._images = occurrence.detection_images
      .filter((src: string) => !!src.length)
      .map((src: string) => ({ src }))
  }

  get categoryLabel(): string {
    return this._occurrence.determination.name
  }

  get categoryScore(): string {
    return 'WIP'
  }

  get deploymentLabel(): string {
    return this._occurrence.deployment.name
  }

  get deploymentId(): string {
    return `${this._occurrence.deployment.id}`
  }

  get id(): string {
    return `${this._occurrence.id}`
  }

  get idLabel(): string {
    return `#${this.id}`
  }

  get images(): { src: string }[] {
    return this._images
  }

  get sessionId(): string {
    return `${this._occurrence.event.id}`
  }

  get sessionLabel(): string {
    return `Session #${this.sessionId}`
  }

  get sessionTimespan(): string {
    return this._occurrence.event.date_label
  }
}
