import { doc, getDoc, setDoc, updateDoc } from 'firebase/firestore';
import { db } from '../firebase'; 

export const saveUserSubscription = async (userEmail: string, data: any) => {
    const userRef = doc(db, 'subscription', userEmail);
    const userDoc = await getDoc(userRef);

    if (!userDoc.exists()) {
        // Create the user document if it doesn't exist
        await setDoc(userRef, { userEmail: userEmail, subscription: data });
        console.log('Created new user document with subscription.');
    } else {
        // Update existing document
        await updateDoc(userRef, { userEmail: userEmail, subscription: data });
        console.log('Updated existing user subscription.');
    }

    // Fetch and return updated data
    const updatedDoc = await getDoc(userRef);
    const userData = updatedDoc.data();
    console.log('User data:', userData);
    return userData;
};


export const savePointsFromSubscription = async (userEmail: string, points: number) => {

    const pointsRef = doc(db, 'userPoints', userEmail);
    const userDoc = await getDoc(pointsRef);

    if (!userDoc.exists()) {
        // Create the user document if it doesn't exist
        await setDoc(pointsRef, { userEmail: userEmail, points: points });
        console.log('Created new user document with points.');
    }
    else {
        // Update existing document
        await updateDoc(pointsRef, { points: points });
        console.log('Updated existing user points.');
    }

    const updatedDoc = await getDoc(pointsRef);
    const userData = updatedDoc.data();
    console.log('User data:', userData);
    return userData;
}

export const getUserPoints = async (userEmail: string) => {
    const pointsRef = doc(db, 'userPoints', userEmail);
    const userDoc = await getDoc(pointsRef);

    if (userDoc.exists()) {
        const userData = userDoc.data();
        return userData?.points || 0; // Return points or 0 if not found
    } else {
        console.log('No such document!');
        return 0;
    }
}

export const removeUserPoints = async (userEmail: string, points: number) => {
    const pointsRef = doc(db, 'userPoints', userEmail);
    const userDoc = await getDoc(pointsRef);

    if (userDoc.exists()) {
        const userData = userDoc.data();
        const currentPoints = userData?.points || 0;

        // Check if the points to remove are greater than the current points
        if (currentPoints >= points) {
            await updateDoc(pointsRef, { points: currentPoints - points });
            console.log('User points updated successfully.');
        } else {
            console.log('Not enough points to remove.');
        }
    } else {
        console.log('No such document!');
    }
}