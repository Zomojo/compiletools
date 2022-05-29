%global owner Zomojo
%global srcname compiletools
%global sum C++ build tools that requires almost no configuration.
%global version_base 4.1.81
%global version_release 1

Summary: %sum
Name: python3-%{srcname}
Version: %{version_base}
Release: %{version_release}%{?org_tag}%{?dist}
Source0: https://github.com/%{owner}/%{srcname}/archive/v%{version_base}.tar.gz
License: GPLv3+
Group: Development/Libraries
Buildroot: %_tmppath/%{name}-%{version}
BuildArch: noarch
Url: http://zomojo.github.io/compiletools/

%if 0%{?rhel:1}
# Can now assume rhel exists

%if %{rhel} == 7
BuildRequires: python36-setuptools python36-configargparse python36-appdirs python36-psutil python36-devel python36-docutils
Requires: python36-setuptools python36-configargparse python36-appdirs python36-psutil
%else
BuildRequires: python3-setuptools python3-configargparse python3-appdirs python3-psutil python3-devel python3-docutils make gcc-c++
Requires: python3-setuptools python3-configargparse python3-appdirs python3-psutil
%endif 

%endif 

Obsoletes: cake python-%{srcname}
Provides: cake python-%{srcname}


%description
%sum

%prep
%autosetup -p0 -n %{srcname}-%{version}

%build
./create-documentation
python3 setup.py build

%if 0%{?rhel:1}
%if %{rhel} < 28
# For some unknown reason this test is failing on a mock F28 but runs fine on development F28 machines
%check
python3 setup.py test
%endif
%endif

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_mandir}/man1/
mkdir -p %{buildroot}%{_datadir}/licenses/python-%{srcname}/

install -m 0644 -t %{buildroot}%{_mandir}/man1/ man1/*.1

# --root $RPM_BUILD_ROOT makes the package install with a single, expanded
# directory in %{python2_sitelib} and a separate egginfo directory.
python3 setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

# Make cake point to ct-cake
pushd %{buildroot}%{_bindir}/
ln -s ct-cake cake
popd

%clean
rm -rf %{buildroot}

%files
%{!?_licensedir:%global license %%doc}
%license LICENSE.txt
%doc README.rst
%{_mandir}/man1/*.1.gz
%{python3_sitelib}/*
%{_bindir}/ct-*
%{_bindir}/cake

%changelog
