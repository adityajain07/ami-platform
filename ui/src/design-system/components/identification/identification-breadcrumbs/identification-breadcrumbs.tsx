import { Fragment } from 'react'
import { Icon, IconTheme, IconType } from '../../icon/icon'
import styles from './identification-breadcrumbs.module.scss'

interface IdentificationBreadcrumbsProps {
  items: {
    id: string
    title: string
  }[]
}

export const IdentificationBreadcrumbs = ({
  items,
}: IdentificationBreadcrumbsProps) => (
  <div className={styles.breadcrumbs}>
    {items.map((item, index) => (
      <Fragment key={item.id}>
        <span className={styles.breadcrumb}>{item.title}</span>
        {index < items.length - 1 ? (
          <Icon
            type={IconType.ToggleRight}
            theme={IconTheme.Neutral}
            size={8}
          />
        ) : null}
      </Fragment>
    ))}
  </div>
)
