import { Deployment, ServerDeployment } from './deployment'

export type ServerProject = any // TODO: Update this type

interface SummaryData {
  title: string
  data: {
    x: (string | number)[]
    y: number[]
    tickvals?: (string | number)[]
    ticktext?: string[]
  }
  type: any
}

export class Project {
  private readonly _project: ServerProject
  private readonly _deployments: Deployment[] = []

  public constructor(project: ServerProject) {
    this._project = project
    this._deployments = (project.deployments ?? []).map(
      (deployment: ServerDeployment) => new Deployment(deployment)
    )
  }

  get description(): string {
    return this._project.description
  }

  get id(): string {
    return `${this._project.id}`
  }

  get image(): string | undefined {
    return this._project.image ? `${this._project.image}` : undefined
  }

  get name(): string {
    return this._project.name
  }

  get deployments(): Deployment[] {
    return this._deployments
  }

  get summaryData(): SummaryData[] {
    return this._project.summary_data
  }
}
