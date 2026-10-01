from rest_framework.routers import DefaultRouter

from .views import CollegeViewSet, NSSUnitViewSet, UniversityViewSet

router = DefaultRouter(trailing_slash=True)
router.register("universities", UniversityViewSet, basename="university")
router.register("colleges", CollegeViewSet, basename="college")
router.register("nss-units", NSSUnitViewSet, basename="nss-unit")

urlpatterns = router.urls
