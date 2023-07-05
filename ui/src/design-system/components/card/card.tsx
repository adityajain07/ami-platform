import styles from './card.module.scss'

interface CardProps {
  title: string
  subTitle: string
  image?: {
    src: string
    alt?: string
  }
  maxWidth?: string
}

export const Card = ({ title, subTitle, image, maxWidth }: CardProps) => {
  return (
    <div className={styles.container} style={{ maxWidth }}>
      <div className={styles.square}>
        {image ? (
          <img src={image.src} alt={image.alt} className={styles.image} />
        ) : (
          <span className={styles.placeholder}>🪲</span>
        )}
      </div>
      <div className={styles.footer}>
        <span className={styles.title}>{title}</span>
        <span className={styles.subTitle}>{subTitle}</span>
      </div>
    </div>
  )
}
