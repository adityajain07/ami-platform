import classNames from 'classnames'
import { FormField } from 'components/form/form-field'
import { DeploymentFieldValues } from 'data-services/models/deployment-details'
import { Button, ButtonTheme } from 'design-system/components/button/button'
import _ from 'lodash'
import { useContext } from 'react'
import { useForm } from 'react-hook-form'
import { FormContext } from 'utils/formContext/formContext'
import { isEmpty } from 'utils/isEmpty/isEmpty'
import { STRING, translate } from 'utils/language'
import { useSyncSectionStatus } from 'utils/useSyncSectionStatus'
import styles from '../../styles.module.scss'
import { config } from '../config'
import { Section } from '../types'

type SectionGeneralFieldValues = Pick<
  DeploymentFieldValues,
  'name' | 'description'
>

const DEFAULT_VALUES: SectionGeneralFieldValues = {
  description: '',
  name: '',
}

export const SectionGeneral = ({ onNext }: { onNext: () => void }) => {
  const { formSectionRef, formState, setFormSectionValues } =
    useContext(FormContext)

  const { control, handleSubmit } = useForm<SectionGeneralFieldValues>({
    defaultValues: {
      ...DEFAULT_VALUES,
      ..._.omitBy(formState[Section.General].values, isEmpty),
    },
    mode: 'onBlur',
  })

  useSyncSectionStatus(Section.General, control)

  return (
    <form
      ref={formSectionRef}
      onSubmit={handleSubmit((values) =>
        setFormSectionValues(Section.General, values)
      )}
    >
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>
          {translate(STRING.FIELD_LABEL_GENERAL)}
        </h2>
        <div className={styles.sectionContent}>
          <div className={styles.sectionRow}>
            <FormField name="name" control={control} config={config} />
            <FormField name="description" control={control} config={config} />
          </div>
        </div>
      </div>
      <div className={classNames(styles.section, styles.formActions)}>
        <Button
          label={translate(STRING.NEXT)}
          onClick={onNext}
          theme={ButtonTheme.Success}
        />
      </div>
    </form>
  )
}
