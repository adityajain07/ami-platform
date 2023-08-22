import collections
import datetime
import itertools
import logging
import textwrap
import typing
import urllib.parse
from datetime import timedelta
from enum import Enum
from typing import Final, final  # noqa: F401

from django.apps import apps
from django.db import IntegrityError, models
from django.db.models import Q

import ami.utils

#: That's how constants should be defined.
_POST_TITLE_MAX_LENGTH: Final = 80
_CLASSIFICATION_TYPES = ("machine", "human", "ground_truth")


class TaxonRank(Enum):
    ORDER = "Order"
    FAMILY = "Family"
    GENUS = "Genus"
    SPECIES = "Species"

    @classmethod
    def choices(cls):
        """For use in Django text fields with choices."""
        return tuple((i.value, i.name) for i in cls)


# @TODO move to settings & make configurable
_SOURCE_IMAGES_URL_BASE = "https://static.dev.insectai.org/ami-trapdata/vermont/snapshots/"
_CROPS_URL_BASE = "https://static.dev.insectai.org/ami-trapdata/crops"


as_choices = lambda x: [(i, i) for i in x]  # noqa: E731

logger = logging.getLogger(__name__)


def shift_to_nighttime(hours: list[int], values: list) -> tuple[list[int], list]:
    """Shift hours so that the x-axis is centered around 12PM."""

    split_index = 0
    for i, hour in enumerate(hours):
        if hour > 12:
            split_index = i
            break

    hours = hours[split_index:] + hours[:split_index]
    values = values[split_index:] + values[:split_index]

    return hours, values


class BaseModel(models.Model):
    """ """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """All django models should have this method."""
        if hasattr(self, "name"):
            name = getattr(self, "name") or "Untitled"
            return name
        else:
            return f"{self.__class__.__name__} #{self.pk}"

    class Meta:
        abstract = True


@final
class Project(BaseModel):
    """ """

    name = models.CharField(max_length=_POST_TITLE_MAX_LENGTH)
    description = models.TextField()
    image = models.ImageField(upload_to="projects", blank=True, null=True)

    # Backreferences for type hinting
    deployments: models.QuerySet["Deployment"]

    def deployments_count(self) -> int:
        return self.deployments.count()

    def taxa(self) -> models.QuerySet["Taxon"]:
        return Taxon.objects.filter(Q(occurrences__project=self)).distinct()

    def taxa_count(self):
        return self.taxa().count()

    def summary_data(self):
        """
        Data prepared for rendering charts with plotly.js on the overview page.

        const EXAMPLE_DATA = {
            y: [18, 45, 98, 120, 109, 113, 43],
            x: ['8PM', '9PM', '10PM', '11PM', '12PM', '13PM', '14PM'],
            tickvals: ['8PM', '', '', '', '', '', '14PM'],
        }

        const EXAMPLE_PLOTS = [
        { title: '19 Jun', data: EXAMPLE_DATA, type: 'bar' },
        { title: '20 Jun', data: EXAMPLE_DATA, type: 'scatter' },
        {
            title: '21 Jun',
            data: EXAMPLE_DATA,
            type: 'scatter',
            showRangeSlider: true,
        }
        """

        plots = []

        # Capture counts per day
        SourceImage = apps.get_model("main", "SourceImage")
        captures_per_date = (
            SourceImage.objects.filter(deployment__project=self)
            .values_list("timestamp__date")
            .annotate(num_capture=models.Count("id"))
            .order_by("timestamp__date")
        )

        if captures_per_date.count():
            days, counts = list(zip(*captures_per_date))
            days = [day for day in days if day]
            # tickvals_per_month = [f"{d:%b}" for d in days]
            tickvals = [f"{days[0]:%b %d}", f"{days[-1]:%b %d}"]
            days = [f"{d:%b %d}" for d in days]
        else:
            days, counts = [], []
            tickvals = []

        plots.append(
            {
                "title": "Captures per day",
                "data": {"x": days, "y": counts, "tickvals": tickvals},
                "type": "bar",
            },
        )

        # Detections per hour
        Detection = apps.get_model("main", "Detection")
        detections_per_hour = (
            Detection.objects.filter(source_image__deployment__project=self)
            .values("source_image__timestamp__hour")
            .annotate(num_detections=models.Count("id"))
            .order_by("source_image__timestamp__hour")
        )

        # hours, counts = list(zip(*detections_per_hour))
        if detections_per_hour.count():
            hours, counts = list(
                zip(*[(d["source_image__timestamp__hour"], d["num_detections"]) for d in detections_per_hour])
            )
            hours, counts = shift_to_nighttime(list(hours), list(counts))
            # @TODO show a tick for every hour even if there are no detections
            hours = [datetime.datetime.strptime(str(h), "%H").strftime("%-I:00 %p") for h in hours]
            ticktext = [f"{hours[0]}:00", f"{hours[-1]}:00"]
        else:
            hours, counts = [], []
            ticktext = []

        plots.append(
            {
                "title": "Detections per hour",
                "data": {"x": hours, "y": counts, "ticktext": ticktext},
                "type": "bar",
            },
        )

        # Line chart of the accumulated number of occurrnces over time throughout the season
        occurrences_per_day = (
            Occurrence.objects.filter(project=self)
            .values_list("event__start")
            .annotate(num_occurrences=models.Count("id"))
            .order_by("event__start")
        )

        if occurrences_per_day.count():
            days, counts = list(zip(*occurrences_per_day))
            # Accumulate the counts
            counts = list(itertools.accumulate(counts))
            # tickvals = [f"{d:%b %d}" for d in days]
            tickvals = [f"{days[0]:%b %d}", f"{days[-1]:%b %d}"]
            days = [f"{d:%b %d}" for d in days]
        else:
            days, counts = [], []
            tickvals = []

        plots.append(
            {
                "title": "Accumulation of occurrences",
                "data": {"x": days, "y": counts, "tickvals": tickvals},
                "type": "line",
            },
        )

        return plots


@final
class Device(BaseModel):
    """Configuration of hardware used to capture images"""

    name = models.CharField(max_length=_POST_TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Device Configuration"


@final
class Site(BaseModel):
    """Research site with multiple deployments"""

    name = models.CharField(max_length=_POST_TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)

    deployments: models.QuerySet["Deployment"]

    def deployments_count(self) -> int:
        return self.deployments.count()

    # def boundary(self) -> Optional[models.GeometryField]:
    # @TODO if/when we use GeoDjango
    #     return None

    def boundary_rect(self) -> tuple[float, float, float, float] | None:
        # Get the minumin and maximum latitude and longitude values of all deployments
        # at this research site.
        min_lat, max_lat, min_lon, max_lon = self.deployments.aggregate(
            min_lat=models.Min("latitude"),
            max_lat=models.Max("latitude"),
            min_lon=models.Min("longitude"),
            max_lon=models.Max("longitude"),
        ).values()

        bounds = (min_lat, min_lon, max_lat, max_lon)
        if None in bounds:
            return None
        else:
            return bounds


@final
class Deployment(BaseModel):
    """
    Class that describes a deployment of a device (camera & hardware) at a research site.
    """

    name = models.CharField(max_length=_POST_TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)

    # @TODO consider sharing only the "data source auth/config" then a one-to-one config for each deployment
    data_source = models.ForeignKey(
        "S3StorageSource", on_delete=models.SET_NULL, null=True, blank=True, related_name="deployments"
    )
    data_source_subdir = models.CharField(max_length=255, blank=True, null=True)
    data_source_regex = models.CharField(max_length=255, blank=True, null=True)
    data_source_last_checked = models.DateTimeField(blank=True, null=True)
    # data_source_last_check_duration = models.DurationField(blank=True, null=True)
    # data_source_last_check_status = models.CharField(max_length=255, blank=True, null=True)
    # data_source_last_check_notes = models.TextField(max_length=255, blank=True, null=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    image = models.ImageField(upload_to="deployments", blank=True, null=True)

    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, related_name="deployments")

    research_site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        related_name="deployments",
    )

    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, related_name="deployments")

    events: models.QuerySet["Event"]
    captures: models.QuerySet["SourceImage"]
    occurrences: models.QuerySet["Occurrence"]

    def events_count(self) -> int:
        return self.events.count()

    def captures_count(self) -> int:
        return self.captures.count()

    def detections_count(self) -> int:
        return Detection.objects.filter(Q(source_image__deployment=self)).count()

    def occurrences_count(self) -> int:
        return self.occurrences.count()

    def taxa(self) -> models.QuerySet["Taxon"]:
        return Taxon.objects.filter(Q(occurrences__deployment=self)).distinct()

    def taxa_count(self) -> int:
        return self.taxa().count()

    def example_captures(self, num=10) -> models.QuerySet["SourceImage"]:
        return SourceImage.objects.filter(deployment=self).order_by("-size")[:num]

    def capture_images(self, num=5) -> list[str]:
        return [c.url() for c in self.example_captures(num)]

    def data_source_uri(self) -> str | None:
        if self.data_source:
            uri = self.data_source.uri().rstrip("/")
            if self.data_source_subdir:
                uri = f"{uri}/{self.data_source_subdir.strip('/')}/"
            if self.data_source_regex:
                uri = f"{uri}?regex={self.data_source_regex}"
        else:
            uri = None
        return uri

    def import_captures(self) -> int:
        """Import images from the deployment's data source"""

        deployment = self
        assert deployment.data_source, f"Deployment {deployment.name} has no data source configured"

        s3_config = deployment.data_source.config
        total_size = 0
        total_files = 0
        new_source_images = []
        for obj in ami.utils.s3.list_files_paginated(
            s3_config,
            subdir=self.data_source_subdir,
            regex_filter=self.data_source_regex,
        ):
            total_files += 1
            total_size += obj["Size"]

            timestamp = ami.utils.dates.get_image_timestamp_from_filename(obj["Key"])
            existing = SourceImage.objects.filter(
                Q(deployment=deployment, path=obj["Key"]) | Q(deployment=deployment, timestamp=timestamp)
            ).first()
            if existing:
                logger.info(f"Skipping existing SourceImage {existing.path}")
            else:
                source_image = SourceImage(
                    deployment=deployment,
                    path=obj["Key"],
                    timestamp=timestamp,
                    last_modified=obj["LastModified"],
                    size=obj["Size"],
                    checksum=obj["ETag"].strip('"'),
                    checksum_algorithm=obj.get("ChecksumAlgorithm"),
                )
                logger.debug(f"Preparing to create SourceImage {source_image.path}")
                source_image.update_calculated_fields()
                new_source_images.append(source_image)

        logger.info(f"Bulk inserting batch of {len(new_source_images)} new SourceImages")
        try:
            # If there are duplicate SourceImages with a batch, ignore_conflicts should prevent an error.
            # But i'm not sure what the downstream effects of this are.
            SourceImage.objects.bulk_create(new_source_images, batch_size=500, ignore_conflicts=True)
        except IntegrityError as e:
            logger.error(f"Error bulk inserting batch of SourceImages: {e}")

        deployment.data_source_last_checked = datetime.datetime.now()
        deployment.save()

        # @TODO can we create events during the initial indexing of images so we don't have to wait?
        events = group_images_into_events(deployment)
        for event in events:
            set_dimensions_from_first_image(event)

        # @TODO compare total_files to the number of SourceImages for this deployment
        # @TODO decide if we should delete SourceImages that are no longer in the data source

        return total_files

    def save(self, *args, **kwargs):
        # Since Occurrences have their own relationship to Project, we need to update
        # the project on all occurrences when the deployment's project changes.
        # @TODO consider if Occurrences need their own relationship to Project.
        if self.pk is not None:
            old = Deployment.objects.get(pk=self.pk)
            if old.project != self.project:
                self.occurrences.update(project=self.project)
        super().save(*args, **kwargs)


@final
class Event(BaseModel):
    """A monitoring session"""

    group_by = models.CharField(
        max_length=255,
        db_index=True,
        help_text=(
            "A unique identifier for this event, used to group images into events. "
            "This allows images to be prepended or appended to an existing event. "
            "The default value is the day the event started, in the format YYYY-MM-DD. "
            "However images could also be grouped by camera settings, image dimensions, hour of day, "
            "or a random sample."
        ),
    )

    start = models.DateTimeField(db_index=True, help_text="The timestamp of the first image in the event.")
    end = models.DateTimeField(null=True, blank=True, help_text="The timestamp of the last image in the event.")

    deployment = models.ForeignKey(Deployment, on_delete=models.SET_NULL, null=True, related_name="events")

    captures: models.QuerySet["SourceImage"]
    occurrences: models.QuerySet["Occurrence"]

    class Meta:
        ordering = ["start"]
        indexes = [
            models.Index(fields=["group_by"]),
            models.Index(fields=["start"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["deployment", "group_by"], name="unique_event"),
        ]

    def __str__(self) -> str:
        return f"{self.start.strftime('%A')}, {self.date_label()}"

    def name(self) -> str:
        return str(self)

    def day(self) -> datetime.date:
        """
        Consider the start of the event to be the day it occurred on.

        Most overnight monitoring sessions will start in the evening and end the next morning.
        """
        return self.start.date()

    def date_label(self) -> str:
        """
        Format the date range for display.

        If the start and end dates are different, display them as:
        Jan 1-5, 2021
        """
        if self.end and self.end.date() != self.start.date():
            return f"{self.start.strftime('%b %-d')}-{self.end.strftime('%-d %Y')}"
        else:
            return f"{self.start.strftime('%b %-d %Y')}"

    def duration(self):
        """Return the duration of the event.

        If the event is still in progress, use the current time as the end time.
        """
        now = datetime.datetime.now(tz=self.start.tzinfo)
        if not self.end:
            return now - self.start
        return self.end - self.start

    def duration_label(self) -> str:
        return ami.utils.dates.format_timedelta(self.duration())

    # These are now loaded with annotations in EventViewSet
    # But the serializer complains if they're not defined here.
    def captures_count(self) -> int | None:
        # return self.captures.distinct().count()
        return None

    def occurrences_count(self) -> int | None:
        # return self.occurrences.distinct().count()
        return None

    def detections_count(self) -> int | None:
        # return Detection.objects.filter(Q(source_image__event=self)).count()
        return None

    def stats(self) -> dict[str, int | None]:
        return (
            SourceImage.objects.filter(event=self)
            .annotate(count=models.Count("detections"))
            .aggregate(
                detections_max_count=models.Max("count"),
                detections_min_count=models.Min("count"),
                detections_avg_count=models.Avg("count"),
            )
        )

    def taxa_count(self) -> int:
        return self.taxa().count()

    def taxa(self) -> models.QuerySet["Taxon"]:
        return Taxon.objects.filter(Q(occurrences__event=self)).distinct()

    def example_captures(self, num=5):
        return SourceImage.objects.filter(event=self).order_by("-size")[:num]

    def first_capture(self):
        return SourceImage.objects.filter(event=self).order_by("timestamp").first()

    def summary_data(self):
        """
        Data prepared for rendering charts with plotly.js
        """
        plots = []

        # Detections per hour
        Detection = apps.get_model("main", "Detection")
        detections_per_hour = (
            Detection.objects.filter(source_image__event=self)
            .values("source_image__timestamp__hour")
            .annotate(num_detections=models.Count("id"))
            .order_by("source_image__timestamp__hour")
        )

        # hours, counts = list(zip(*detections_per_hour))
        if detections_per_hour:
            hours, counts = list(
                zip(*[(d["source_image__timestamp__hour"], d["num_detections"]) for d in detections_per_hour])
            )
            hours, counts = shift_to_nighttime(list(hours), list(counts))
            # @TODO show a tick for every hour even if there are no detections
            hours = [datetime.datetime.strptime(str(h), "%H").strftime("%-I:00 %p") for h in hours]
            ticktext = [f"{hours[0]}:00", f"{hours[-1]}:00"]
        else:
            hours, counts = [], []
            ticktext = []

        plots.append(
            {
                "title": "Detections per hour",
                "data": {"x": hours, "y": counts, "ticktext": ticktext},
                "type": "bar",
            },
        )

        # Horiziontal bar chart of top taxa
        Taxon = apps.get_model("main", "Taxon")
        top_taxa = (
            Taxon.objects.filter(occurrences__event=self)
            .values("name")
            # .annotate(num_detections=models.Count("occurrences__detections"))
            .annotate(num_detections=models.Count("occurrences"))
            .order_by("-num_detections")
        )

        if top_taxa:
            taxa, counts = list(zip(*[(t["name"], t["num_detections"]) for t in top_taxa]))
            taxa = [t or "Unknown" for t in taxa]
            counts = [c or 0 for c in counts]
        else:
            taxa, counts = [], []

        plots.append(
            {
                "title": "Top species",
                "data": {"x": counts, "y": taxa},
                "type": "bar",
                "orientation": "h",
            },
        )

        return plots

    def save(self, *args, **kwargs):
        if not self.group_by and self.start:
            # If no group_by is set, use the start "day"
            self.group_by = self.start.date()

        if self.pk is not None:
            # Can only update start and end times if this is an update to an existing event
            first = self.captures.order_by("timestamp").values("timestamp").first()
            last = self.captures.order_by("-timestamp").values("timestamp").first()
            if first:
                self.start = first["timestamp"]
            if last:
                self.end = last["timestamp"]
        super().save(*args, **kwargs)


def group_images_into_events(
    deployment: Deployment, max_time_gap=timedelta(minutes=120), delete_empty=True
) -> list[Event]:
    image_timestamps = list(
        SourceImage.objects.filter(deployment=deployment)
        .exclude(timestamp=None)
        .values_list("timestamp", flat=True)
        .order_by("timestamp")
        .distinct()
    )

    timestamp_groups = ami.utils.dates.group_datetimes_by_gap(image_timestamps, max_time_gap)

    events = []
    for group in timestamp_groups:
        if not len(group):
            continue

        start_date = group[0]
        end_date = group[-1]

        # Print debugging info about groups
        delta = end_date - start_date
        hours = round(delta.seconds / 60 / 60, 1)
        logger.debug(
            f"Found session starting at {start_date} with {len(group)} images that ran for {hours} hours.\n"
            f"From {start_date.strftime('%c')} to {end_date.strftime('%c')}."
        )

        # Creating events & assigning images
        group_by = start_date.date()
        event, _ = Event.objects.get_or_create(
            deployment=deployment,
            group_by=group_by,
            defaults={"start": start_date, "end": end_date},
        )
        events.append(event)
        SourceImage.objects.filter(deployment=deployment, timestamp__in=group).update(event=event)
        logger.info(f"Created/updated event {event} with {len(group)} images for deployment {deployment}.")

    if delete_empty:
        delete_empty_events()

    return events


def delete_empty_events(dry_run=False):
    """
    Delete events that have no images, occurrences or other related records.
    """

    # @TODO Search all models that have a foreign key to Event
    # related_models = [
    #     f.related_model
    #     for f in Event._meta.get_fields()
    #     if f.one_to_many or f.one_to_one or (f.many_to_many and f.auto_created)
    # ]

    events = Event.objects.annotate(num_images=models.Count("captures")).filter(num_images=0)
    events = events.annotate(num_occurrences=models.Count("occurrences")).filter(num_occurrences=0)

    if dry_run:
        for event in events:
            print(f"Would delete event {event}")
    else:
        print(f"Deleting {events.count()} empty events")
        events.delete()


@final
class S3StorageSource(BaseModel):
    """
    Per-deployment configuration for an S3 bucket.
    """

    name = models.CharField(max_length=255)
    bucket = models.CharField(max_length=255)
    prefix = models.CharField(max_length=255, blank=True)
    access_key = models.TextField()
    secret_key = models.TextField()
    endpoint_url = models.CharField(max_length=255, blank=True, null=True)
    public_base_url = models.CharField(max_length=255, blank=True)
    total_size = models.BigIntegerField(null=True, blank=True)
    total_files = models.BigIntegerField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    # last_check_duration = models.DurationField(null=True, blank=True)
    # use_signed_urls = models.BooleanField(default=False)

    deployments: models.QuerySet["Deployment"]

    @property
    def config(self):
        return ami.utils.s3.S3Config(
            bucket_name=self.bucket,
            prefix=self.prefix,
            access_key_id=self.access_key,
            secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            public_base_url=self.public_base_url,
        )

    def list_files(self, limit=None):
        """Recursively list files in the bucket/prefix."""

        return ami.utils.s3.list_files_paginated(self.config)

    def count_files(self):
        """Count & save the number of files in the bucket/prefix."""

        count = ami.utils.s3.count_files_paginated(self.config)
        self.total_files = count
        self.save()
        return count

    def calculate_size(self):
        """Calculate the total size and count of all files in the bucket/prefix."""

        sizes = [obj["Size"] for obj in self.list_files()]
        size = sum(sizes)
        count = len(sizes)
        self.total_size = size
        self.total_files = count
        self.save()
        return size

    def uri(self, path: str | None = None):
        """Return the full URI for the given path."""

        full_path = "/".join(str(part).strip("/") for part in [self.bucket, self.prefix, path] if part)
        return f"s3://{full_path}"

    def public_url(self, path: str):
        """Return the public URL for the given path."""

        return ami.utils.s3.public_url(self.config, path)

    # If the public_base_url has changed, update all the source images
    def save(self, *args, **kwargs):
        if self.pk is not None:
            old = S3StorageSource.objects.get(pk=self.pk)
            if old.public_base_url != self.public_base_url:
                for deployment in self.deployments.all():
                    deployment.captures.update(public_base_url=self.public_base_url)
        super().save(*args, **kwargs)


@final
class SourceImage(BaseModel):
    """A single image captured during a monitoring session"""

    path = models.CharField(max_length=255, blank=True)
    public_base_url = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(null=True, blank=True, db_index=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    last_modified = models.DateTimeField(null=True, blank=True)
    checksum = models.CharField(max_length=255, blank=True, null=True)
    checksum_algorithm = models.CharField(max_length=255, blank=True, null=True)

    # project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, related_name="source_images")
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, related_name="captures", db_index=True)
    deployment = models.ForeignKey(Deployment, on_delete=models.SET_NULL, null=True, related_name="captures")

    detections: models.QuerySet["Detection"]

    def __str__(self) -> str:
        return f"{self.__class__.__name__} #{self.pk} {self.path}"

    def public_url(self) -> str:
        """
        Return the public URL for this image.

        The base URL is determined by the deployment's data source and is cached
        on the source image. If the deployment's data source changes, the URLs
        for all source images will be updated.

        @TODO use signed URLs if necessary.
        @TODO add support for thumbnail URLs here?
        @TODO consider if we ever need to access the original image directly!
        """
        return urllib.parse.urljoin(self.public_base_url or "/", self.path)

    # backwards compatibility
    url = public_url

    def detections_count(self) -> int | None:
        # return self.detections.count()
        return None

    def get_base_url(self) -> str:
        """
        Determine the public URL from the deployment's data source.

        If there is no data source, return a relative URL.
        """
        if self.deployment and self.deployment.data_source and self.deployment.data_source.public_base_url:
            return self.deployment.data_source.public_base_url
        else:
            return "/"

    def extract_timestamp(self) -> datetime.datetime | None:
        """
        Extract a timestamp from the filename or EXIF data
        """
        # @TODO use EXIF data if necessary (use methods in AMI data companion repo)
        timestamp = ami.utils.dates.get_image_timestamp_from_filename(self.path)
        if not timestamp:
            # timestamp = ami.utils.dates.get_image_timestamp_from_exif(self.path)
            msg = f"No timestamp could be extracted from the filename or EXIF data of {self.path}"
            logger.error(msg)
        return timestamp

    def get_dimensions(self) -> tuple[int | None, int | None]:
        """Calculate the width and height of the original image."""
        if self.path and self.deployment and self.deployment.data_source:
            config = self.deployment.data_source.config
            img = ami.utils.s3.read_image(config=config, key=self.path)
            self.width, self.height = img.size
            self.save()
            return self.width, self.height
        else:
            return None, None

    def update_calculated_fields(self):
        if self.path and not self.timestamp:
            self.timestamp = self.extract_timestamp()
        if self.path and not self.public_base_url:
            self.public_base_url = self.get_base_url()

    def save(self, *args, **kwargs):
        self.update_calculated_fields()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ("deployment", "event", "timestamp")

        # Add two "unique together" constraints to prevent duplicate images
        constraints = [
            # deployment + path (only one image per deployment with a given file path)
            models.UniqueConstraint(fields=["deployment", "path"], name="unique_deployment_path"),
            # deployment + timestamp (only on image per deployment at a given moment in time)
            models.UniqueConstraint(fields=["deployment", "timestamp"], name="unique_deployment_timestamp"),
        ]

        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["event"]),
        ]


def set_dimensions_from_first_image(event: Event, replace_existing: bool = False):
    """
    Calculate the width and height of the first image in an event and
    update all of the images in the event with the same dimensions.
    """

    first_image = event.captures.first()
    if first_image:
        if not first_image.width or not first_image.height:
            first_image.get_dimensions()
        logger.info(
            f"Setting dimensions for {event.captures.count()} images in event {event.pk} to "
            f"{first_image.width}x{first_image.height}"
        )
        if replace_existing:
            captures = event.captures.all()
        else:
            captures = event.captures.filter(width__isnull=True, height__isnull=True)
        captures.update(width=first_image.width, height=first_image.height)


@final
class ClassificationResult(BaseModel):
    """A classification result from a model"""

    pass


@final
class Classification(BaseModel):
    """The output of a classifier"""

    detection = models.ForeignKey(
        "Detection",
        on_delete=models.SET_NULL,
        null=True,
        related_name="classifications",
    )

    # @TODO maybe use taxon instead of determination. Determination is for the final ID of the occurrence
    determination = models.ForeignKey("Taxon", on_delete=models.SET_NULL, null=True, related_name="classifications")
    score = models.FloatField(null=True)
    timestamp = models.DateTimeField()

    softmax_output = models.JSONField(null=True)  # scores for all classes
    raw_output = models.JSONField(null=True)  # raw output from the model

    algorithm = models.ForeignKey(
        "Algorithm",
        on_delete=models.SET_NULL,
        null=True,
    )
    # job = models.CharField(max_length=255, null=True)

    # @TODO maybe ML classification and human classificaions should be separate models?
    type = models.CharField(max_length=255, choices=as_choices(_CLASSIFICATION_TYPES))

    class Meta:
        constraints = [
            # Ensure that the type is one of the allowed values at the database level
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_type_valid",
                check=models.Q(
                    type__in=_CLASSIFICATION_TYPES,
                ),
            ),
        ]


@final
class Algorithm(BaseModel):
    """A machine learning algorithm"""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)

    classfications: models.QuerySet["Classification"]


@final
class Detection(BaseModel):
    """An object detected in an image"""

    source_image = models.ForeignKey(
        SourceImage,
        on_delete=models.CASCADE,
        related_name="detections",
    )

    bbox = models.JSONField(null=True, blank=True)

    timestamp = models.DateTimeField(null=True, blank=True)

    # file = (
    #     models.ImageField(
    #         null=True,
    #         blank=True,
    #         upload_to="detections",
    #     ),
    # )
    path = models.CharField(max_length=255, blank=True)

    occurrence = models.ForeignKey(
        "Occurrence",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detections",
    )
    frame_num = models.IntegerField(null=True, blank=True)

    detection_algorithm = models.ForeignKey(
        "Algorithm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    detection_time = models.DateTimeField(null=True, blank=True)
    detection_score = models.FloatField(null=True, blank=True)
    # detection_job = models.ForeignKey(
    #     "Job",
    #     on_delete=models.SET_NULL,
    #     null=True,
    # )

    similarity_vector = models.JSONField(null=True, blank=True)

    classifications: models.QuerySet["Classification"]

    # def bbox(self):
    #     return (
    #         self.bbox_x,
    #         self.bbox_y,
    #         self.bbox_width,
    #         self.bbox_height,
    #     )

    # def bbox_coords(self):
    #     return (
    #         self.bbox_x,
    #         self.bbox_y,
    #         self.bbox_x + self.bbox_width,
    #         self.bbox_y + self.bbox_height,
    #     )

    # def bbox_percent(self):
    #     return (
    #         self.bbox_x / self.source_image.width,
    #         self.bbox_y / self.source_image.height,
    #         self.bbox_width / self.source_image.width,
    #         self.bbox_height / self.source_image.height,
    #     )

    def width(self) -> int | None:
        if self.bbox and len(self.bbox) == 4:
            return self.bbox[2] - self.bbox[0]

    def height(self) -> int | None:
        if self.bbox and len(self.bbox) == 4:
            return self.bbox[3] - self.bbox[1]

    class Meta:
        ordering = [
            "frame_num",
            "timestamp",
        ]

    def best_classification(self):
        classification = (
            self.classifications.order_by("-score")
            .select_related("determination", "determination__name", "score")
            .first()
        )
        if classification and classification.determination:
            return (classification.determination.name, classification.score)
        else:
            return (None, None)

    def url(self):
        # @TODO use settings
        # urllib.parse.urljoin(settings.MEDIA_URL, self.path)
        url = urllib.parse.urljoin(_CROPS_URL_BASE, self.path)
        return url


@final
class Occurrence(BaseModel):
    """An occurrence of a taxon, a sequence of one or more detections"""

    determination = models.ForeignKey("Taxon", on_delete=models.SET_NULL, null=True, related_name="occurrences")
    # determination_score = models.FloatField(null=True, blank=True)

    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, related_name="occurrences")
    deployment = models.ForeignKey(Deployment, on_delete=models.SET_NULL, null=True, related_name="occurrences")
    project = models.ForeignKey("Project", on_delete=models.SET_NULL, null=True, related_name="occurrences")

    detections: models.QuerySet[Detection]

    def detections_count(self) -> int | None:
        # Annotaions don't seem to work with nested serializers
        return self.detections.count()

    # @TODO cache first_apperance timestamp
    def first_appearance(self) -> SourceImage | None:
        first = self.detections.order_by("timestamp").select_related("source_image").first()
        if first:
            return first.source_image

    def last_appearance(self) -> SourceImage | None:
        last = self.detections.order_by("-timestamp").select_related("source_image").first()
        if last:
            return last.source_image

    def duration(self) -> datetime.timedelta | None:
        first = self.first_appearance()
        last = self.last_appearance()
        if first and last and first.timestamp and last.timestamp:
            return last.timestamp - first.timestamp
        else:
            return None

    def duration_label(self) -> str | None:
        return ami.utils.dates.format_timedelta(self.duration())

    def detection_images(self, limit=None):
        for url in Detection.objects.filter(occurrence=self).values_list("path", flat=True)[:limit]:
            yield urllib.parse.urljoin(_CROPS_URL_BASE, url)

    def best_detection(self):
        return Detection.objects.filter(occurrence=self).order_by("-classifications__score").first()

    def determination_score(self) -> float | None:
        return (
            Classification.objects.filter(detection__occurrence=self)
            .order_by("-created_at")
            .aggregate(models.Max("score"))["score__max"]
        )

    def determination_algorithm(self) -> Algorithm | None:
        return Algorithm.objects.filter(classification__detection__occurrence=self).first()

    def context_url(self):
        detection = self.best_detection()
        if detection and detection.source_image and detection.source_image.event:
            return f"https://app.preview.insectai.org/sessions/{detection.source_image.event.pk}?capture={detection.source_image.pk}&occurrence={self.pk}"  # noqa E501
        else:
            return None

    def url(self):
        return f"https://app.preview.insectai.org/occurrences/{self.pk}"


@final
class TaxaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()

    def add_species_parents(self):
        """Add parents to all species that don't have them.

        Create a genus if it doesn't exist based on the scientific name of the species.
        This will replace any parents of a species that are not of the GENUS rank.
        """
        species = self.get_queryset().filter(rank="SPECIES")  # , parent=None)
        updated = []
        for taxon in species:
            if taxon.parent and taxon.parent.rank == "GENUS":
                continue
            genus_name = taxon.name.split()[0]
            genus = self.get_queryset().filter(name=genus_name, rank="GENUS").first()
            if not genus:
                Taxon = self.model
                genus = Taxon.objects.create(name=genus_name, rank="GENUS")
            taxon.parent = genus
            logger.info(f"Added parent {genus} to {taxon}")
            taxon.save()
            updated.append(taxon)
        return updated

    # Method that returns taxa nested in a tree structure
    def tree(self, root: typing.Optional["Taxon"] = None) -> dict:
        """Build a recursive tree of taxa."""

        root = root or self.root()

        # Fetch all taxa
        taxa = self.get_queryset().filter(active=True)

        # Build index of taxa by parent
        taxa_by_parent = collections.defaultdict(list)
        for taxon in taxa:
            taxa_by_parent[taxon.parent].append(taxon)

        # Recursively build a nested tree
        def _tree(taxon):
            return {
                "taxon": taxon,
                "children": [_tree(child) for child in taxa_by_parent[taxon]],
            }

        return _tree(root)

    def tree_of_names(self, root: typing.Optional["Taxon"] = None) -> dict:
        """
        Build a recursive tree of taxon names.

        Names in the database are not not formatted as nicely as the python-rendered versions.
        """

        root = root or self.root()

        # Fetch all names and parent names
        names = self.get_queryset().filter(active=True).values_list("name", "parent__name")

        # Index names by parent name
        names_by_parent = collections.defaultdict(list)
        for name, parent_name in names:
            names_by_parent[parent_name].append(name)

        # Recursively build a nested tree

        def _tree(name):
            return {
                "name": name,
                "children": [_tree(child) for child in names_by_parent[name]],
            }

        return _tree(root.name)

    def root(self):
        """Get the root taxon, the one with no parent and the highest taxon rank."""

        for rank in list(TaxonRank):
            taxon = self.get_queryset().filter(parent=None, rank=rank.name).first()
            if taxon:
                return taxon

        root = self.get_queryset().filter(parent=None).first()
        assert root, "No root taxon found"
        return root


@final
class Taxon(BaseModel):
    """A taxonomic classification"""

    name = models.CharField(max_length=255, unique=True)
    rank = models.CharField(max_length=255, choices=TaxonRank.choices(), default=TaxonRank.SPECIES.name)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, related_name="direct_children")
    parents = models.ManyToManyField("self", related_name="children", symmetrical=False)
    active = models.BooleanField(default=True)
    synonym_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="synonyms")

    direct_children: models.QuerySet["Taxon"]
    children: models.QuerySet["Taxon"]
    occurrences: models.QuerySet[Occurrence]
    classifications: models.QuerySet["Classification"]
    lists: models.QuerySet["TaxaList"]

    authorship_date = models.DateField(null=True, blank=True, help_text="The date the taxon was described.")
    ordering = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        # @TODO cache this version of the name in the database?
        if self.rank == "SPECIES":
            return self.name
        elif self.rank == "GENUS":
            return f"{self.name} sp."
        elif self.rank not in ["ORDER", "FAMILY"]:
            return f"{self.name} ({self.rank})"
        else:
            return self.name

    def num_direct_children(self) -> int:
        return self.direct_children.count()

    def num_children_recursive(self) -> int:
        # @TODO how to do this with a single query?
        return self.children.count() + sum(child.num_children_recursive() for child in self.children.all())

    def occurrences_count(self) -> int:
        # return self.occurrences.count()
        return 0

    def detections_count(self) -> int:
        # return Detection.objects.filter(occurrence__determination=self).count()
        return 0

    def events_count(self) -> int:
        return 0

    def latest_occurrence(self) -> Occurrence | None:
        return self.occurrences.order_by("-created_at").first()

    def latest_detection(self) -> Detection | None:
        return Detection.objects.filter(occurrence__determination=self).order_by("-created_at").first()

    def last_detected(self) -> datetime.datetime | None:
        # This is handled by an annotation
        return None

    def occurrence_images(self):
        """
        Return one image from each occurrence of this Taxon.
        The image should be from the detection with the highest classification score.
        """

        # @TODO Can we use a single query
        for occurrence in self.occurrences.prefetch_related("detections__classifications").all():
            detection = occurrence.detections.order_by("-classifications__score").first()
            if detection:
                yield detection.url()

    def list_names(self) -> str:
        return ", ".join(self.lists.values_list("name", flat=True))

    objects = TaxaManager()

    class Meta:
        ordering = [
            "ordering",
            "name",
        ]
        verbose_name_plural = "Taxa"


@final
class TaxaList(BaseModel):
    """A checklist of taxa"""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    taxa = models.ManyToManyField(Taxon, related_name="lists")

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Taxa Lists"


@final
class BlogPost(BaseModel):
    """
    This model is used just as an example.

    With it we show how one can:
    - Use fixtures and factories
    - Use migrations testing

    """

    title = models.CharField(max_length=_POST_TITLE_MAX_LENGTH)
    body = models.TextField()

    class Meta:
        verbose_name = "Blog Post"  # You can probably use `gettext` for this
        verbose_name_plural = "Blog Posts"

    def __str__(self) -> str:
        """All django models should have this method."""
        return textwrap.wrap(self.title, _POST_TITLE_MAX_LENGTH // 4)[0]


# These come directly from Celery
_JOB_STATES = ["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED", "RECEIVED"]


default_job_config = {
    "input": {
        "name": "Captures",
        "size": 100,
    },
    "stages": [
        {
            "name": "Object Detection",
            "key": "object_detection",
            "params": [
                {"key": "model", "name": "Localization Model", "value": "yolov5s"},
                {"key": "batch_size", "name": "Batch size", "value": 8},
                # {"key": "threshold", "name": "Threshold", "value": 0.5},
                {"key": "input_size", "name": "Images processed", "read_only": True},
                {"key": "output_size", "name": "Objects detected", "read_only": True},
            ],
        },
        {
            "name": "Objects of Interest Filter",
            "key": "binary_classification",
            "params": [
                {"key": "algorithm", "name": "Binary classification model", "value": "resnet18"},
                {"key": "batch_size", "name": "Batch size", "value": 8},
                {"key": "input_size", "name": "Objects processed", "read_only": True},
                {"key": "output_size", "name": "Objects of interest", "read_only": True},
            ],
        },
        {
            "name": "Species Classification",
            "key": "species_classification",
            "params": [
                {"key": "algorithm", "name": "Species classification model", "value": "resnet18"},
                {"key": "batch_size", "name": "Batch size", "value": 8},
                {"key": "threshold", "name": "Confidence threshold", "value": 0.5},
                {"key": "input_size", "name": "Species processed", "read_only": True},
                {"key": "output_size", "name": "Species classified", "read_only": True},
            ],
        },
        {
            "name": "Occurrence Tracking",
            "key": "tracking",
            "params": [
                {"key": "algorithm", "name": "Occurrence tracking algorithm", "value": "adityacombo"},
                {"key": "input_size", "name": "Detections processed", "read_only": True},
                {"key": "output_size", "name": "Occurrences identified", "read_only": True},
            ],
        },
    ],
}

example_non_model_config = {
    "input": {
        "name": "Raw Captures",
        "source": "s3://bucket/path/to/captures",
        "size": 100,
    },
    "stages": [
        {
            "name": "Image indexing",
            "key": "image_indexing",
            "params": [
                {"key": "input_size", "name": "Directories scanned", "read_only": True},
                {"key": "output_size", "name": "Images indexed", "read_only": True},
            ],
        },
        {
            "name": "Image resizing",
            "key": "image_resizing",
            "params": [
                {"key": "width", "name": "Width", "value": 640},
                {"key": "height", "name": "Height", "value": 480},
                {"key": "input_size", "name": "Images processed", "read_only": True},
            ],
        },
        {
            "name": "Feature extraction",
            "key": "feature_extraction",
            "params": [
                {"key": "algorithm", "name": "Feature extractor", "value": "imagenet"},
                {"key": "input_size", "name": "Images processed", "read_only": True},
            ],
        },
    ],
}

default_job_progress = {
    "summary": {"status": "PENDING", "progress": 0, "status_label": "0% completed."},
    "stages": [
        {
            "key": "object_detection",
            "status": "PENDING",
            "progress": 0,
            "status_label": "0% completed.",
            "time_elapsed": 0,
            "time_remaining": None,
            "input_size": 0,
            "output_size": 0,
        },
        {
            "key": "binary_classification",
            "status": "PENDING",
            "progress": 0,
            "status_label": "0% completed.",
            "time_elapsed": 0,
            "time_remaining": None,
            "input_size": 0,
            "output_size": 0,
        },
        {
            "key": "species_classification",
            "status": "PENDING",
            "progress": 0,
            "status_label": "0% completed.",
            "time_elapsed": 0,
            "time_remaining": None,
            "input_size": 0,
            "output_size": 0,
        },
        {
            "key": "tracking",
            "status": "PENDING",
            "progress": 0,
            "time_elapsed": 0,
            "time_remaining": None,
            "input_size": 0,
            "output_size": 0,
        },
    ],
}


class Job(BaseModel):
    """A job to be run by the scheduler

    Example config:
    """

    name = models.CharField(max_length=255)
    config = models.JSONField(default=default_job_config, null=True, blank=False)
    queue = models.CharField(max_length=255, default="default")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=255, default="PENDING", choices=as_choices(_JOB_STATES))
    progress = models.JSONField(default=default_job_progress, null=True, blank=False)
    result = models.JSONField(null=True, blank=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="jobs")
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="jobs", null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    @classmethod
    def default_config(cls) -> dict:
        return default_job_config

    @classmethod
    def default_progress(cls) -> dict:
        """Return the progress of each stage of this job as a dictionary"""
        return default_job_progress


@final
class Page(BaseModel):
    """Barebones page model for static pages like About & Contact."""

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True, help_text="Unique, URL safe name e.g. about-us")
    content = models.TextField("Body content", blank=True, null=True, help_text="Use Markdown syntax")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="pages", null=True, blank=True)
    link_class = models.CharField(max_length=255, blank=True, null=True, help_text="CSS class for nav link")
    nav_level = models.IntegerField(default=0, help_text="0 = main nav, 1 = sub nav, etc.")
    nav_order = models.IntegerField(default=0, help_text="Order of nav items within a level")
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["nav_level", "nav_order", "name"]

    def __str__(self) -> str:
        return self.name

    def html(self) -> str:
        """Convert the content field to HTML"""
        from markdown import markdown

        if self.content:
            return markdown(self.content, extensions=[])
        else:
            return ""
