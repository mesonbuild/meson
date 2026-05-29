#!/bin/bash

set -e

source /ci/common.sh
source /ci/env_vars.sh

export DEBIAN_FRONTEND=noninteractive
export LANG='C.UTF-8'

apt-get -y update
apt-get -y upgrade

pkgs=(
  git jq ninja-build python3-pip sdkmanager
)

apt-get -y install "${pkgs[@]}"

install_minimal_python_packages

# cleanup
apt-get -y clean
apt-get -y autoclean

# sdk install

set -x

if [[ -z $ANDROID_HOME || -z $ANDROID_SDKVER || -z $ANDROID_NDKVER ]]; then
    echo "ANDROID_HOME, ANDROID_SDKVER and ANDROID_NDKVER env var must be set!"
    exit 1
fi

mkdir -p ${HOME}/.android
# there are currently zero user repos
echo 'count=0' > ${HOME}/.android/repositories.cfg
cat <<EOF >> ${HOME}/.android/sites-settings.cfg
@version@=1
@disabled@https\://dl.google.com/android/repository/extras/intel/addon.xml=disabled
@disabled@https\://dl.google.com/android/repository/glass/addon.xml=disabled
@disabled@https\://dl.google.com/android/repository/sys-img/android/sys-img.xml=disabled
@disabled@https\://dl.google.com/android/repository/sys-img/android-tv/sys-img.xml=disabled
@disabled@https\://dl.google.com/android/repository/sys-img/android-wear/sys-img.xml=disabled
@disabled@https\://dl.google.com/android/repository/sys-img/google_apis/sys-img.xml=disabled
EOF

ANDROID_SDKMAJOR=${ANDROID_SDKVER%%.*}

# accepted licenses

mkdir -p $ANDROID_HOME/licenses/

cat << EOF > $ANDROID_HOME/licenses/android-sdk-license

8933bad161af4178b1185d1a37fbf41ea5269c55

d56f5187479451eabf01fb78af6dfcb131a6481e

24333f8a63b6825ea9c5514f83c2829b004d1fee
EOF

cat <<EOF > $ANDROID_HOME/licenses/android-sdk-preview-license

84831b9409646a918e30573bab4c9c91346d8abd
EOF

cat <<EOF > $ANDROID_HOME/licenses/android-sdk-preview-license-old

79120722343a6f314e0719f863036c702b0e6b2a

84831b9409646a918e30573bab4c9c91346d8abd
EOF

cat <<EOF > $ANDROID_HOME/licenses/intel-android-extra-license

d975f751698a77b662f1254ddbeed3901e976f5a
EOF

sdkmanager --sdk_root "${ANDROID_HOME}" \
	"ndk;${ANDROID_NDKVER}"

kernel=$(uname -s)
arch=$(uname -m)

tee "${ANDROID_HOME}/toolchain.cross" <<EOF
[constants]
toolchain='${ANDROID_HOME}/ndk/${ANDROID_NDKVER}/toolchains/llvm/prebuilt/${kernel,,}-${arch}'
EOF

/meson_private/meson.py env2mfile --android -o "${ANDROID_HOME}/meson/"
find "${ANDROID_HOME}/meson/" -exec sh -c 'for cf; do jq -nr --arg file "$cf" "{ \"file\": \$file, \"env\": [], \"tests\": [\"common\", \"failing-meson\", \"failing-build\", \"platform-android\"] }" > "${cf%%.txt}.json"; done' sh {} +
